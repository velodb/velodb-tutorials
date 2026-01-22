"""AgentOS server to expose the RAG agent via HTTP."""
from agno.os import AgentOS
from .agent import agent, search
from dotenv import load_dotenv

load_dotenv()


def main():
    """Start the AgentOS server with sample documents."""
    print("\n📚 Loading sample documents...")

    # Add sample documents for demonstration - diverse topics for hybrid search
    sample_docs = [
        # Technology - Kafka
        "Apache Kafka was first released in 2011 as an open-source distributed event streaming platform developed by LinkedIn.",
        "Kafka is designed for high-throughput, fault-tolerant messaging. It is widely used for building real-time data pipelines and streaming applications.",
        "LinkedIn open-sourced Kafka in 2011 and it became an Apache project in 2012. Today it powers messaging at companies like Netflix, Uber, and Airbnb.",

        # Science - Faraday & Electromagnetism
        "Michael Faraday was an English scientist who contributed to the study of electromagnetism and electrochemistry. His main discoveries include electromagnetic induction and the laws of electrolysis.",
        "Faraday discovered electromagnetic induction in 1831, which led to the development of electric generators and transformers.",
        "The Faraday cage is named after Michael Faraday, who invented it in 1836. It blocks electromagnetic fields and is used to protect sensitive electronics.",

        # Space
        "The International Space Station is a modular space station in low Earth orbit. It serves as a microgravity and space environment research laboratory.",
        "The ISS orbits Earth at approximately 400 kilometers altitude, completing one orbit every 90 minutes at a speed of about 28,000 km/h.",
        "NASA, Roscosmos, JAXA, ESA, and CSA collaborate on the International Space Station, which has been continuously occupied since November 2000.",

        # Database - VeloDB
        "VeloDB is a real-time analytics database built on Apache Doris. It supports vector search, full-text search, and hybrid search in a unified SQL interface.",
        "VeloDB combines OLAP analytics with AI capabilities, enabling users to perform semantic search and traditional SQL queries in the same database.",
        "Hybrid search in VeloDB uses RRF (Reciprocal Rank Fusion) to combine BM25 keyword matching with vector similarity search for better retrieval quality.",

        # Programming - Python
        "Python was created by Guido van Rossum and first released in 1991. It emphasizes code readability and supports multiple programming paradigms.",
        "Python is one of the most popular programming languages for data science, machine learning, and artificial intelligence applications.",
        "The Python Package Index (PyPI) hosts over 400,000 packages, making Python one of the most extensible programming languages available.",

        # History - Uruguay
        "Uruguay gained independence in 1828 after a long struggle involving Spain, Portugal, Argentina, and Brazil.",
        "Montevideo, the capital of Uruguay, was founded by the Spanish in 1724 as a military stronghold in the region.",
        "Uruguay is known as the 'Switzerland of South America' due to its stable democracy, social policies, and high standard of living.",

        # Additional tech topics
        "Redis is an in-memory data structure store used as a database, cache, and message broker. It supports various data structures like strings, hashes, and sorted sets.",
        "Elasticsearch is a distributed search and analytics engine built on Apache Lucene. It provides full-text search with an HTTP web interface.",
        "PostgreSQL is a powerful open-source relational database known for its reliability, feature robustness, and SQL compliance.",
    ]

    for doc in sample_docs:
        search.ingest(doc)
    print(f"✅ Loaded {len(sample_docs)} sample documents\n")

    agent_os = AgentOS(
        agents=[agent],
        cors_allowed_origins=["http://localhost:3001", "http://localhost:3000", "http://127.0.0.1:3001", "http://127.0.0.1:3000"]
    )

    print("🚀 VeloDB RAG Agent running!")
    print("   Backend: http://localhost:7777\n")

    agent_os.serve(app=agent_os.get_app(), host="0.0.0.0", port=7777)


if __name__ == "__main__":
    main()
