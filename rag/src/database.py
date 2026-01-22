"""VeloDB client with hybrid search capability."""
import os
import pymysql
from typing import List, Tuple
from dotenv import load_dotenv

load_dotenv()


class VeloDBClient:
    """Client for connecting to VeloDB and performing hybrid search."""

    def __init__(self):
        """Initialize connection to VeloDB using MySQL protocol."""
        self.database = os.getenv("VELODB_DATABASE", "rag_demo")
        # Connect without database first to create it if needed
        self.conn = pymysql.connect(
            host=os.getenv("VELODB_HOST"),
            port=int(os.getenv("VELODB_MYSQL_PORT", "9030")),
            user=os.getenv("VELODB_USER"),
            password=os.getenv("VELODB_PASSWORD"),
            autocommit=True,
        )
        self._setup_schema()

    def _setup_schema(self):
        """Create the documents table with vector and inverted indexes."""
        with self.conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            cur.execute(f"USE {self.database}")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS rag_documents (
                    id BIGINT NOT NULL AUTO_INCREMENT,
                    content TEXT,
                    embedding ARRAY<FLOAT>,
                    INDEX idx_embedding(embedding) USING INVERTED,
                    INDEX idx_content(content) USING INVERTED PROPERTIES("parser"="english")
                ) DUPLICATE KEY(id)
                DISTRIBUTED BY HASH(id) BUCKETS 1
                PROPERTIES ("replication_num" = "1")
            """)

    def insert(self, content: str, embedding: List[float]):
        """Insert a document with its embedding."""
        with self.conn.cursor() as cur:
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            cur.execute(
                "INSERT INTO rag_documents (content, embedding) VALUES (%s, %s)",
                (content, embedding_str),
            )

    def hybrid_search(
        self, query: str, query_embedding: List[float], top_k: int = 5
    ) -> List[Tuple]:
        """
        Perform hybrid search: vector + BM25 + RRF fusion in one query.

        Returns: List of (id, content, vector_score, text_score, hybrid_score)
        """
        with self.conn.cursor() as cur:
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
            safe_query = query.replace("'", "\\'")

            sql = f"""
                WITH vector_results AS (
                    SELECT
                        id, content,
                        1 - cosine_distance(embedding, {embedding_str}) as vector_score,
                        ROW_NUMBER() OVER (ORDER BY cosine_distance(embedding, {embedding_str}) ASC) as vector_rank
                    FROM rag_documents
                    ORDER BY cosine_distance(embedding, {embedding_str}) ASC
                    LIMIT {top_k * 3}
                ),
                text_results AS (
                    SELECT
                        id, content,
                        1.0 as text_score,
                        ROW_NUMBER() OVER (ORDER BY id) as text_rank
                    FROM rag_documents
                    WHERE content MATCH '{safe_query}'
                    LIMIT {top_k * 3}
                ),
                combined AS (
                    SELECT
                        COALESCE(v.id, t.id) as id,
                        COALESCE(v.content, t.content) as content,
                        COALESCE(v.vector_score, 0) as vector_score,
                        COALESCE(t.text_score, 0) as text_score,
                        COALESCE(v.vector_rank, 999) as vector_rank,
                        COALESCE(t.text_rank, 999) as text_rank
                    FROM vector_results v
                    FULL OUTER JOIN text_results t ON v.id = t.id
                )
                SELECT
                    id, content, vector_score, text_score,
                    (0.5 / (60 + vector_rank) + 0.5 / (60 + text_rank)) as hybrid_score
                FROM combined
                ORDER BY hybrid_score DESC
                LIMIT {top_k}
            """
            cur.execute(sql)
            return cur.fetchall()

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
