import asyncio
from typing import List
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import models  # ✅ 引入 models

from app.services.neo4j_service import neo4j_manager
from app.services.qdrant_service import qdrant_manager
from app.services.embedding_factory import embedding_factory
from app.core.logger import logger
from app.core.config import settings

class DataSyncService:
    def __init__(self):
        self.collection_name = settings.COLLECTION_NAME

    async def sync_knowledge_base(self) -> dict:
        logger.info("🔄 [Sync] Neo4j -> Qdrant 全量同步开始...")
        
        # 1. 从 Neo4j 拉数据
        cypher = """
        MATCH (n)
        WHERE n.name IS NOT NULL
        RETURN n.name as name, n.description as desc, labels(n) as labels
        """
        records = neo4j_manager.execute_query(cypher)
        data = getattr(records, 'records', records) or []
        
        logger.info(f"🔄 [Sync] Neo4j 查询到 {len(data)} 条数据: {data[:10]}...")
        
        if not data:
            logger.warning("⚠️ Neo4j 为空，跳过同步")
            return {"status": "skipped", "reason": "neo4j_empty", "count": 0}
        
        # 2. 构造文档
        documents: List[Document] = []
        for record in data:
            name = record.get("name", "")
            desc = record.get("desc", "") or ""
            labels = record.get("labels", [])
            
            entity_type = next((l for l in labels if l != "Entity"), "Unknown")
            
            doc = Document(
                page_content=f"{name} {desc}".strip(),
                metadata={
                    "name": name,
                    "description": desc,
                    "type": entity_type
                }
            )
            documents.append(doc)
        
        # 3. 🔥 v1 最佳实践：手动创建集合 + VectorStore
        client = qdrant_manager.get_client()
        embeddings = embedding_factory.get_embedding()
        
        # 总是确保集合存在
        if not client.collection_exists(self.collection_name):
            try:
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=settings.EMBD_DIMENSIONS,
                        distance=models.Distance.COSINE
                    )
                )
                logger.success(f"✅ 创建新集合: {self.collection_name} (维度: {settings.EMBD_DIMENSIONS})")
            except Exception as e:
                logger.error(f"❌ 创建集合失败: {e}")
                return {"status": "failed", "error": f"create_collection: {e}"}
        else:
            logger.info(f"✅ 使用现有集合: {self.collection_name}")
            # 清空数据（防止重复）
            try:
                collection_info = client.get_collection(self.collection_name)
                if collection_info.points_count > 0:
                    logger.info(f"🗑️ 清空 {collection_info.points_count} 条旧数据")
                    client.delete_collection(self.collection_name)
                    # 重新创建
                    client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=models.VectorParams(
                            size=settings.EMBD_DIMENSIONS,
                            distance=models.Distance.COSINE
                        )
                    )
            except Exception as e:
                logger.warning(f"⚠️ 清空失败，继续使用: {e}")
        
        # ✅ 现在安全初始化 VectorStore
        try:
            vectorstore = QdrantVectorStore(
                client=client,
                collection_name=self.collection_name,
                embedding=embeddings
            )
            
            # 异步批量添加
            if documents:
                await vectorstore.aadd_documents(documents)
            
            # 验证写入
            collection_info = client.get_collection(self.collection_name)
            logger.success(f"✅ 同步完成！实际写入 {collection_info.points_count} 条实体")
            return {"status": "success", "count": len(documents), "actual_count": collection_info.points_count}
            
        except Exception as e:
            logger.error(f"❌ VectorStore 操作失败: {e}")
            return {"status": "failed", "error": str(e), "count": 0}

# 单例
data_sync_service = DataSyncService()