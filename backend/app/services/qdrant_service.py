from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.services.embedding_factory import embedding_factory
from app.core.config import settings
from app.core.logger import logger
import uuid

from typing import List, Dict, Any, Optional

class QdrantManager:
    _client: QdrantClient = None

    def __init__(self):
        self.url = settings.QDRANT_URL
        self.api_key = settings.QDRANT_API_KEY
        self.score_threshold = 0.6
        self._connect()

    def _connect(self):
        try:
            if self.api_key:
                self._client = QdrantClient(url=self.url, api_key=self.api_key)
            else:
                self._client = QdrantClient(path=self.url) if not self.url.startswith("http") else QdrantClient(url=self.url)
            
            logger.success(f"✅ Qdrant 客户端初始化成功: {self.url}")
        except Exception as e:
            logger.error(f"❌ Qdrant 初始化失败: {e}")
            raise e

    def get_client(self) -> QdrantClient:
        """获取原生客户端，方便给 LangChain 使用"""
        return self._client

    def create_collection_if_not_exists(self, collection_name: str, vector_size: int = 4096):
        """
        创建一个集合 (类似 SQL 的 Table)
        vector_size: 向量维度
        """
        
        vector_size = vector_size or settings.EMBD_DIMENSIONS
        
        if not self._client.collection_exists(collection_name):
            self._client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size, 
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"已创建新集合: {collection_name}")
        else:
            logger.info(f"集合已存在: {collection_name}")

    def upsert_vectors(self, 
                       collection_name: str,
                       vectors: List[List[float]], 
                       payloads: List[Dict[str, Any]], 
                       ids: Optional[List[str]] = None):
        """接受向量 直接插入指定集合"""
        try:
            batch_size = len(vectors)
            
            # 如果没有提供 ID，则自动生成 UUID
            if ids is None:
                ids = [str(uuid.uuid4()) for _ in range(batch_size)]
            
            # 构造 Qdrant 需要的 PointStruct 列表
            points = [
                models.PointStruct(
                    id=ids[i],
                    vector=vectors[i],
                    payload=payloads[i]
                )
                for i in range(batch_size)
            ]

            # 执行 Upsert 操作
            self._client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.success(f"✅ 成功插入/更新 {batch_size} 条数据到集合 {collection_name}")
            return True
        except Exception as e:
            logger.error(f"❌ 插入向量失败: {e}")
            return False
        
    def add_texts(self, 
                  collection_name: str,
                  texts: List[str],
                  metadatas: List[Dict[str, Any]] = None):
        """
        高层方法：直接接收文本，内部自动完成 Embedding 并存入 Qdrant
        """
        if not texts:
            return
            
        if metadatas is None:
            metadatas = [{"text": text} for text in texts] # 默认把文本存入 payload
            
        try:
            # 1. 获取 Embedding 模型
            embeddings_model = embedding_factory.get_embedding()
            
            # 2. 将文本转为向量 (Batch)
            logger.info(f"⏳ 正在生成 {len(texts)} 条文本的 Embeddings...")
            vectors = embeddings_model.embed_documents(texts)
            
            # 3. 存入 Qdrant
            self.upsert_vectors(collection_name, vectors, metadatas)
            
        except Exception as e:
            logger.error(f"❌ add_texts 处理流程失败: {e}")
            raise e
            

    def search(self, collection_name: str, query_vector: list, limit: int = 5):
        """搜索功能"""
        response = self._client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
            score_threshold=self.score_threshold,
            with_payload=True        # 显式声明需要返回 payload (原文内容)
        )

        return response.points

# --- 单例导出 ---
try:
    qdrant_manager = QdrantManager()
except Exception:
    qdrant_manager = None

if __name__ == "__main__":
    if qdrant_manager:
        test_col = "test_knowledge_base"
        
        # 1. 确保集合存在 (注意 vector_size 要和 EmbeddingFactory 的维度一致)
        qdrant_manager.create_collection_if_not_exists(test_col, vector_size=settings.EMBD_DIMENSIONS) 
        
        # 2. 准备测试数据
        texts = [
            "Qdrant 是一个高性能的向量数据库。",
            "Python 是一种非常流行的编程语言。",
            "今晚吃什么好呢？"
        ]
        metadatas = [
            {"source": "doc1", "category": "tech", "content": texts[0]},
            {"source": "doc2", "category": "tech", "content": texts[1]},
            {"source": "doc3", "category": "life", "content": texts[2]},
        ]

        # 3. 执行插入 (自动 Embedding + Upsert)
        logger.info("🚀 开始插入测试数据...")
        qdrant_manager.add_texts(test_col, texts, metadatas)
        
        # 4. 执行搜索测试
        logger.info("🔍 开始搜索 '数据库'...")
        # 为了搜索，我们需要先把查询词变成向量
        emb_model = embedding_factory.get_embedding()
        query_vec = emb_model.embed_query("数据库")
        
        results = qdrant_manager.search(test_col, query_vec, limit=2)
        
        for res in results:
            print(f"找到结果 (得分: {res.score:.4f}): {res.payload['content']}")