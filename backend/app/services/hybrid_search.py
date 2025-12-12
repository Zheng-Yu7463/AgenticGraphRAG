import asyncio
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_qdrant import QdrantVectorStore
from qdrant_client import models
from langchain_core.output_parsers import PydanticOutputParser

from app.services.embedding_factory import embedding_factory
from app.services.llm_factory import llm_factory
from app.services.neo4j_service import neo4j_manager
from app.services.qdrant_service import qdrant_manager
from app.prompts.extraction import entity_extraction_prompt
from app.core.logger import logger
from app.core.config import settings

# --- 数据结构定义 ---
class ExtractionFormat(BaseModel):
    entities: Any = Field(..., description="实体列表")
    
    @property
    def flat_entities(self) -> List[str]:
        """🦾 智能适配所有可能的 DeepSeek 输出格式"""
        entities_raw = self.entities
        
        # 情况1：直接是字符串列表
        if isinstance(entities_raw, list) and all(isinstance(e, str) for e in entities_raw):
            return [e.strip() for e in entities_raw if e.strip()]
        
        # 情况2：实体对象数组 [{"name": "...", "type": "..."}]
        elif isinstance(entities_raw, list):
            all_names = []
            for item in entities_raw:
                if isinstance(item, dict):
                    all_names.append(item.get("name", "") or item.get("entity", ""))
                elif isinstance(item, str):
                    all_names.append(item)
            return [e.strip() for e in all_names if e.strip()]
        
        # 情况3：分类字典 {"person": [...], "company": [...]}
        elif isinstance(entities_raw, dict):
            all_entities = []
            for category, items in entities_raw.items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, str):
                            all_entities.append(item)
                        elif isinstance(item, dict):
                            all_entities.append(item.get("name", "") or item.get("entity", ""))
            return [e.strip() for e in all_entities if e.strip()]
        
        return []

class HybridSearchService:
    def __init__(self):
        self.embeddings = embedding_factory.get_embedding()
        self.qdrant_vectorstore = None
        self.neo4j_driver = neo4j_manager
        
        # 1. 初始化 Qdrant
        self._init_qdrant()
        
        # 2. 初始化提取器 components
        # 我们把 Parser 存为成员变量，以便后续获取 instructions
        self.extraction_parser = PydanticOutputParser(pydantic_object=ExtractionFormat)
        self.extraction_chain = self._init_extraction()
        
        logger.success("✅ HybridSearch初始化完成")

    def _init_qdrant(self):
        """Qdrant实体库初始化（带自动建表功能）"""
        client = qdrant_manager.get_client()
        collection_name = settings.COLLECTION_NAME
        
        if not client.collection_exists(collection_name):
            try:
                dummy_vec = self.embeddings.embed_query("test")
                vector_size = len(dummy_vec)
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE
                    )
                )
                logger.success(f"✅ 已创建新集合: {collection_name}")
            except Exception as e:
                logger.error(f"❌ Qdrant 建表失败: {e}")

        self.qdrant_vectorstore = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=self.embeddings
        )

    def _init_extraction(self):
        """初始化提取链：Prompt | LLM | Parser"""
        llm = llm_factory.get_llm(mode="fast")
        # 构造 LCEL Chain
        # 注意：这里我们使用了之前保存的 self.extraction_parser
        chain = entity_extraction_prompt | llm | self.extraction_parser
        return chain

    async def search(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        # Step 1: LLM抽实体
        entities = await self._extract_entities(query)
        
        if not entities:
            logger.info("未提取到实体，fallback 到纯向量检索")
            return {
                "context_text": "",
                "entities": [],
                "matched_entities": [],
                "graph_context": "无实体"
            }
        
        # Step 2: Qdrant找相似实体
        matched_entities = await self._qdrant_match_entities(entities, top_k)
        
        logger.info(f"🔍 [RETRIEVAL]: 匹配到实体: {matched_entities}")
        
        # Step 3: Neo4j查图信息
        graph_context = await self._neo4j_get_graph(matched_entities)

        logger.info(f"🔍 [RETRIEVAL]: 查找到图谱关系: {graph_context}")

        # 组装上下文
        context_parts = []
        if matched_entities:
            names = [e['name'] for e in matched_entities[:3]]
            context_parts.append(f"涉及实体：{', '.join(names)}")
        if graph_context:
            context_parts.append(f"知识图谱关系：\n{graph_context}")
        return {
            "context_text": "\n".join(context_parts),
            "entities": entities,
            "matched_entities": matched_entities,
            "graph_context": graph_context
        }

    async def _extract_entities(self, query: str) -> List[str]:
        """LLM实体提取"""
        try:
            # 🔴 核心修复：使用 .ainvoke() 而不是直接调用 ()
            result: ExtractionFormat = await self.extraction_chain.ainvoke({
                "query": query,
                "text": query, # 这里假设 text 就是 query 本身
                "format_instructions": self.extraction_parser.get_format_instructions()
            })
            
            entities = result.flat_entities
            logger.info(f"提取实体: {entities}")
            return entities
        except Exception as e:
            logger.warning(f"实体提取失败: {e}")
            return []

    async def _qdrant_match_entities(self, entities: List[str], top_k: int) -> List[Dict]:
        if not self.qdrant_vectorstore or not entities:
            return []

        tasks = []
        for entity in entities[:3]:
            # 并发查询
            tasks.append(self.qdrant_vectorstore.asimilarity_search_with_score(entity, k=2))
        
        results_groups = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_results = []
        for i, group in enumerate(results_groups):
            if isinstance(group, Exception):
                continue
            
            origin_query = entities[i]
            for doc, score in group:
                payload = doc.metadata
                all_results.append({
                    "name": payload.get("name", origin_query),
                    "score": float(score),
                    "type": payload.get("type", "unknown")
                })

        unique_results = {}
        for r in all_results:
            name = r["name"]
            if name not in unique_results or r["score"] > unique_results[name]["score"]:
                unique_results[name] = r
        
        return sorted(unique_results.values(), key=lambda x: x["score"], reverse=True)[:top_k]

    async def _neo4j_get_graph(self, matched_entities: List[Dict]) -> str:
        if not self.neo4j_driver or not matched_entities:
            return ""
            
        entity_names = [e["name"] for e in matched_entities[:3]]
        
        cypher = """
        MATCH (s:Entity)-[r]-(t:Entity)
        WHERE s.name IN $names
        RETURN s.name as source, type(r) as rel, t.name as target
        LIMIT 15
        """
        
        try:
            records = self.neo4j_driver.execute_query(cypher, {"names": entity_names})
            data = getattr(records, 'records', records)
            if not data: return "无直接关联信息"

            relations = []
            for record in data:
                src = record.get('source') if isinstance(record, dict) else record['source']
                rel = record.get('rel') if isinstance(record, dict) else record['rel']
                tgt = record.get('target') if isinstance(record, dict) else record['target']
                relations.append(f"{src} -[{rel}]-> {tgt}")
            
            return "\n".join(relations)
        except Exception as e:
            logger.warning(f"Neo4j查询失败: {e}")
            return ""

hybrid_search_service = None

def init_hybrid_search():
    """
    在 FastAPI 启动时调用此函数进行初始化
    """
    global hybrid_search_service
    try:
        hybrid_search_service = HybridSearchService()
        logger.success("🚀 HybridSearchService 全局实例已创建")
    except Exception as e:
        logger.error(f"❌ HybridSearchService 初始化失败: {e}")


if __name__ == "__main__":
    async def test():
        if hybrid_search_service:
            tests = [
                "马斯克的太空公司是什么",
                "SpaceX和星舰的关系", 
                "特斯拉在中国建厂了吗"
            ]
            for query in tests:
                print(f"\n{'='*60}")
                print(f"🔍 {query}")
                result = await hybrid_search_service.search(query)
                logger.info(f"简要上下文: {result['context_text']}")
                logger.info(f"抽取实体: {result['entities']}")
                logger.info(f"匹配实体: {result['matched_entities']}")
                logger.info(f"图谱: {result['graph_context']}")
    
    asyncio.run(test())