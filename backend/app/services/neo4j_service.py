from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, Driver
from app.core.config import settings
from app.core.logger import logger

class Neo4jManager:
    _driver: Driver = None

    def __init__(self):
        """初始化连接"""
        self.uri = settings.NEO4J_URI
        self.user = settings.NEO4J_USERNAME
        self.password = settings.NEO4J_PASSWORD
        self._connect()

    def _connect(self):
        """内部连接方法"""
        try:
            self._driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
            # 验证连接
            self._driver.verify_connectivity()
            logger.success(f"✅ Neo4j 连接成功: {self.uri}")
        except Exception as e:
            logger.error(f"❌ Neo4j 连接失败: {e}")
            raise e

    def close(self):
        """关闭连接"""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j 连接已关闭")

    def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        执行 Cypher 查询并返回字典列表
        
        Args:
            query: Cypher 语句
            parameters: 参数字典
            
        Returns:
            List[Dict]: 结果列表，每项都是一个纯 Python 字典
        """
        if not self._driver:
            logger.warning("⚠️ 驱动未检测到，尝试重新连接...")
            self._connect()
            
        # 确保参数不为 None
        if parameters is None:
            parameters = {}

        try:
            # 使用 Eager Result API (Driver 5.x+)
            result = self._driver.execute_query(
                query, 
                parameters_=parameters,
                database_="neo4j" # 默认数据库通常是 neo4j
            )
            
            # 🔥 关键优化：将 Record 对象转换为纯字典
            # result.records 包含原生对象，record.data() 转换为 dict
            clean_results = [record.data() for record in result.records]
            
            return clean_results

        except Exception as e:
            logger.error(f"❌ Cypher 执行出错:\nQuery: {query}\nError: {e}")
            # 这里可以选择 raise e 或者返回空列表，视业务需求而定
            raise e

    # --- 👇 GraphRAG 常用辅助功能 👇 ---

    def clear_database(self):
        """⚠️ 危险操作：清空整个数据库"""
        logger.warning("正在清空 Neo4j 数据库...")
        query = "MATCH (n) DETACH DELETE n"
        self.execute_query(query)
        logger.success("🗑️ Neo4j 数据库已清空")
        
    def check_health(self) -> Dict[str, Any]:
        """检查 Neo4j 连接状态"""
        if not self._driver:
            return {"status": "down", "error": "Driver not initialized"}
        
        try:
            # 验证连接
            self._driver.verify_connectivity()
            return {
                "status": "healthy",
                "address": self.uri
            }
        except Exception as e:
            logger.error(f"Neo4j 健康检查失败: {e}")
            return {"status": "down", "error": str(e)}

# --- 单例导出 ---
try:
    neo4j_manager = Neo4jManager()
except Exception:
    neo4j_manager = None 

# --- 测试代码 ---
if __name__ == "__main__":
    if neo4j_manager:
        logger.info("🚀 开始 Neo4j 测试...")
        
        # 1. 写入测试 (Merge 保证幂等性)
        insert_cql = """
        MERGE (p:Person {name: $name}) 
        SET p.role = $role 
        RETURN p.name as name, p.role as role
        """
        params = {"name": "Neo", "role": "The One"}
        
        results = neo4j_manager.execute_query(insert_cql, params)
        logger.info(f"写入结果: {results}") 
        # 现在的 results 直接是 [{'name': 'Neo', 'role': 'The One'}]，非常干净

        # 2. 读取测试
        read_cql = "MATCH (n:Person) RETURN n.name as name, n.role as role"
        read_results = neo4j_manager.execute_query(read_cql)
        print(f"查询到的数据: {read_results}")

        neo4j_manager.close()
