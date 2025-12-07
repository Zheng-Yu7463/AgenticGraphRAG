import asyncio
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from langchain_qdrant import Qdrant
from langchain.agents import create_agent

from app.services.embedding_factory import embedding_factory
from app.services.llm_factory import llm_factory
from app.services.neo4j_service import neo4j_manager
from app.services.qdrant_service import qdrant_manager
from app.core.logger import logger

class ExtractionFormat(BaseModel):
    entities: List[str] = Field(..., description="提取的实体列表, 如人名, 公司名, 产品名等，必须与原文一字不差")

class HybridSearchService:
    """
    🚀 LLM抽实体 → Qdrant相似匹配 → Neo4j图信息
    """
    
    def __init__(self):
        self.embeddings = embedding_factory.get_embedding()
        self.qdrant_vectorstore = None
        self.neo4j_driver = neo4j_manager
        self.extraction_chain = self._init_extraction()
        self._init_qdrant()
        logger.success("✅ HybridSearch初始化完成")
        

    def _init_qdrant(self):
        """Qdrant实体库"""
        client = qdrant_manager.get_client()
        self.qdrant_vectorstore = Qdrant(
            client=client,
            collection_name="entities",
            embeddings=self.embeddings
        )
        logger.success("✅ Qdrant实体库初始化")

    def _init_extraction(self):
        """LLM实体抽取"""
        llm = llm_factory.get_llm(mode="fast")
        extraction_agent = create_agent(
            model=llm,
            system_prompt="你是一个专业的信息提取助手，从查询中提取专有名词实体，原封不动返回他们",
            response_format=ExtractionFormat,
        )
        return extraction_agent

    async def search(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """核心检索：3步走"""
        
        # Step 1: LLM抽实体
        entities = await self._extract_entities(query)
        if not entities:
            return {"context_text": "未提取到实体", "entities": []}
        
        # Step 2: Qdrant找相似实体
        matched_entities = await self._qdrant_match_entities(entities, top_k)
        
        # Step 3: Neo4j查图信息
        graph_context = await self._neo4j_get_graph(matched_entities)
        
        context = f"相关实体：{', '.join([e['name'] for e in matched_entities[:3]])}\n图谱信息：{graph_context}"
        
        return {
            "context_text": context,
            "entities": entities,
            "matched_entities": matched_entities,
            "graph_context": graph_context
        }

    async def _extract_entities(self, query: str) -> List[str]:
        """LLM实体提取"""
        try:
            result = await self.extraction_chain.ainvoke({"query": query})
            last_message = result['messages'][-1]
            print(last_message)
            structured_output = last_message.additional_kwargs.get('response_format', {})
            entities = structured_output.get('entities', [])
            logger.info(f"提取实体: {entities}")
        except Exception as e:
            logger.warning(f"实体提取失败: {e}")
            return []

    async def _qdrant_match_entities(self, entities: List[str], top_k: int) -> List[Dict]:
        """Qdrant相似匹配"""
        if not self.qdrant_vectorstore or not entities:
            return []
            
        all_results = []
        for entity in entities[:3]:  # 最多查3个
            try:
                docs = self.qdrant_vectorstore.similarity_search_with_score(entity, k=2)
                for doc, score in docs:
                    payload = doc.metadata
                    all_results.append({
                        "name": payload.get("name", entity),
                        "matched_query": entity,
                        "score": float(score),
                        "description": doc.page_content[:100]
                    })
            except Exception as e:
                logger.warning(f"Qdrant检索失败: {e}")
        
        # 按分数排序去重
        unique_results = {}
        for r in all_results:
            name = r["name"]
            if name not in unique_results or r["score"] > unique_results[name]["score"]:
                unique_results[name] = r
        
        return sorted(unique_results.values(), key=lambda x: x["score"], reverse=True)[:top_k]

    async def _neo4j_get_graph(self, matched_entities: List[Dict]) -> str:
        """Neo4j查图信息"""
        if not self.neo4j_driver or not matched_entities:
            return "无图谱信息"
            
        entity_names = [e["name"] for e in matched_entities[:3]]
        
        cypher = """
        MATCH (s:Entity)-[r]-(t:Entity)
        WHERE s.name IN $names OR t.name IN $names
        RETURN s.name as source, type(r) as rel_type, t.name as target
        LIMIT 10
        """
        
        try:
            records = self.neo4j_driver.execute_query(cypher, {"names": entity_names})
            
            relations = []
            for record in getattr(records, 'records', records) or []:
                relations.append(f"{record.get('source', 'N/A')} --[{record.get('rel_type', 'REL')}]--> {record.get('target', 'N/A')}")
            
            return "; ".join(relations) if relations else "无直接关系"
        except Exception as e:
            logger.warning(f"Neo4j查询失败: {e}")
            return "图谱查询失败"

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