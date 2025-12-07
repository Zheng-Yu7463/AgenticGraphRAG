import asyncio
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from qdrant_client import models
from langchain_qdrant import QdrantVectorStore
from langchain_core.prompts import ChatPromptTemplate

from app.services.embedding_factory import embedding_factory
from app.services.llm_factory import llm_factory
from app.services.neo4j_service import neo4j_manager
from app.services.qdrant_service import qdrant_manager
from app.core.logger import logger

# 定义输出结构
class ExtractionFormat(BaseModel):
    entities: Any = Field(..., description="实体，支持任意格式")
    
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
        
        # 情况4：其他情况，返回空
        return []
    

class HybridSearchService:
    def __init__(self):
        self.embeddings = embedding_factory.get_embedding()
        self.qdrant_vectorstore = None
        self.neo4j_driver = neo4j_manager
        # 初始化组件
        self._init_qdrant()
        self.extraction_chain = self._init_extraction()
        logger.success("✅ HybridSearch初始化完成")

    def _init_qdrant(self):
        """Qdrant实体库初始化（带自动建表功能）"""
        client = qdrant_manager.get_client()
        collection_name = "test-collection"
        
        # 🛠️ 关键步骤 1: 检查集合是否存在
        if not client.collection_exists(collection_name):
            logger.warning(f"⚠️ 集合 '{collection_name}' 不存在，正在自动创建...")
            
            # 🛠️ 关键步骤 2: 动态获取向量维度
            # 为了防止维度填错，我们先用 embedding 模型跑一个测试词，获取准确的维度
            try:
                dummy_vec = self.embeddings.embed_query("test")
                vector_size = len(dummy_vec)
            except Exception as e:
                logger.error(f"❌ 无法获取 Embedding 维度: {e}")
                raise e

            # 🛠️ 关键步骤 3: 创建集合
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,      # 自动匹配你的模型维度
                    distance=models.Distance.COSINE # 推荐使用余弦相似度
                )
            )
            logger.success(f"✅ 已创建新集合: {collection_name} (维度: {vector_size})")

        # 正常初始化 LangChain 组件
        self.qdrant_vectorstore = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=self.embeddings
        )
        logger.success("✅ Qdrant实体库初始化完成")

    def _init_extraction(self):
        llm = llm_factory.get_llm(mode="fast")
        
        def extract_entities(query: str, text: str) -> ExtractionFormat:
            structured_llm = llm.with_structured_output(
                ExtractionFormat,
                method="json_mode"
            )
            return structured_llm.invoke([
                ("system", """提取查询相关的实体，返回 JSON 格式。

    支持格式：
    1. {{"entities": ["马斯克", "SpaceX"]}}  ← 推荐
    2. {{"entities": [{{"name": "SpaceX", "type": "公司"}}]}} 
    3. {{"entities": {{"person": ["马斯克"], "company": ["SpaceX"]}}}}

    实体类型：人名、公司、产品、地名等"""),
                ("user", f"查询：{query}\n\n文本：{text}")
            ])
        
        return extract_entities

    async def search(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        # Step 1: LLM抽实体
        entities = await self._extract_entities(query)
        
        # 💡 改进：如果没有实体，不要直接返回空，
        # 在真实的混合检索中，这里应该 Fallback 到对“文档切片”的纯向量检索
        if not entities:
            logger.info("未提取到实体，fallback 到纯向量检索")
            return {
                "context_text": "",
                "entities": [],
                "matched_entities": [],  # ✅ 添加这个字段
                "graph_context": "无实体"
            }
        # Step 2: Qdrant找相似实体 (已优化为并发)
        matched_entities = await self._qdrant_match_entities(entities, top_k)
        
        # Step 3: Neo4j查图信息
        graph_context = await self._neo4j_get_graph(matched_entities)
        
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
        try:
            result: ExtractionFormat = self.extraction_chain(query, query)
            entities = result.flat_entities  # 🔥 智能扁平化
            logger.info(f"提取实体: {entities}")
            return entities
        except Exception as e:
            logger.warning(f"实体提取失败: {e}")
            return []
        
    async def _qdrant_match_entities(self, entities: List[str], top_k: int) -> List[Dict]:
        if not self.qdrant_vectorstore or not entities:
            return []

        # ⚡ 优化：并发查询 Qdrant
        tasks = []
        for entity in entities[:3]:
            tasks.append(self.qdrant_vectorstore.asimilarity_search_with_score(entity, k=2))
        
        results_groups = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_results = []
        for i, group in enumerate(results_groups):
            if isinstance(group, Exception):
                logger.warning(f"Qdrant某项查询失败: {group}")
                continue
            
            origin_query = entities[i]
            for doc, score in group:
                payload = doc.metadata
                all_results.append({
                    "name": payload.get("name", origin_query), # 假设 metadata 里存了标准名
                    "score": float(score),
                    "type": payload.get("type", "unknown")
                })

        # 去重逻辑保持不变
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
        
        # Cypher 优化：增加 LIMIT 防止爆炸，返回更友好的格式
        cypher = """
        MATCH (s:Entity)-[r]-(t:Entity)
        WHERE s.name IN $names
        RETURN s.name as source, type(r) as rel, t.name as target
        LIMIT 15
        """
        
        try:
            # 注意：这里需要确认 neo4j_manager.execute_query 是同步还是异步
            # 如果是官方 driver，通常是用 session.run，这里假设你封装了 execute_query
            # 如果支持异步驱动，最好也用 await
            records = self.neo4j_driver.execute_query(cypher, {"names": entity_names})
            
            # 处理返回值，适配不同的 Neo4j driver 封装
            data = getattr(records, 'records', records)
            if not data: 
                return "无直接关联信息"

            relations = []
            for record in data:
                # 兼容字典访问或对象访问
                src = record.get('source') if isinstance(record, dict) else record['source']
                rel = record.get('rel') if isinstance(record, dict) else record['rel']
                tgt = record.get('target') if isinstance(record, dict) else record['target']
                relations.append(f"{src} -[{rel}]-> {tgt}")
            
            return "\n".join(relations)
        except Exception as e:
            logger.warning(f"Neo4j查询失败: {e}")
            return ""

# ... 实例化和测试代码保持不变 ...

# 单例
try:
    hybrid_search_service = HybridSearchService()
except Exception as e:
    logger.error(f"❌ 初始化失败: {e}")
    hybrid_search_service = None

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