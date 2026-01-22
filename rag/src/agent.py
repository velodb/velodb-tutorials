"""Agno agent with RAG toolkit for VeloDB hybrid search."""
import os
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from .search import HybridSearch

# Initialize search
search = HybridSearch()


def search_knowledge(query: str, top_k: int = 3) -> str:
    """
    Search the knowledge base using VeloDB hybrid search.

    Args:
        query: The search query
        top_k: Number of results to return (default: 3)

    Returns:
        Formatted context from search results
    """
    try:
        with search.db.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM rag_documents")
            total_docs = cur.fetchone()[0]

            safe_query = query.replace("'", "\\'")
            try:
                cur.execute(f"SELECT COUNT(*) FROM rag_documents WHERE content MATCH '{safe_query}'")
                bm25_matches = cur.fetchone()[0]
            except:
                bm25_matches = 0

        results = search.search(query, top_k)
        if not results:
            return f"No relevant information found.\n\nSearch Statistics:\n- Total documents: {total_docs}\n- BM25 matches: {bm25_matches}"

        stats = f"""Search Statistics:
- Total documents: {total_docs}
- BM25 keyword matches: {bm25_matches}
- Final results after RRF: {len(results)}

"""
        context_parts = [stats]
        for i, (id, content, vector_score, text_score, hybrid_score) in enumerate(results, 1):
            context_parts.append(
                f"[Source {i}] (Hybrid: {hybrid_score:.4f}, Vector: {vector_score:.4f}, BM25: {text_score:.2f})\n{content}\n"
            )
        return "".join(context_parts)
    except Exception as e:
        return f"Error searching: {str(e)}"


def add_document(content: str) -> str:
    """Add a document to the knowledge base."""
    try:
        search.ingest(content)
        return f"Document added successfully ({len(content)} characters)."
    except Exception as e:
        return f"Error adding document: {str(e)}"


# Create OpenRouter model
model = OpenAIChat(
    id="openai/gpt-4o-mini",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

# Create the agent
agent = Agent(
    name="VeloDB RAG Assistant",
    model=model,
    tools=[search_knowledge, add_document],
    instructions=[
        "You are a VeloDB RAG Assistant. Show the hybrid search process clearly.",
        "",
        "## Response Format:",
        "",
        "**🔍 Hybrid Search Flow**",
        "",
        "```",
        "📊 Dataset: Sample knowledge base",
        "   Topics: Technology, Science, History, Databases",
        "",
        "🔤 BM25 Filter: X documents matched keywords",
        "   Keywords: extracted from query",
        "",
        "🧠 Vector Search: Y documents ranked by semantic similarity",
        "   Concept: semantic meaning of query",
        "",
        "⚡ RRF Combined: Z final results (best of both methods)",
        "```",
        "",
        "**✅ Answer**",
        "",
        "{1-2 sentence direct answer}",
        "",
        "**📚 Sources**",
        "",
        "**[1]** Hybrid: score • Vector: score • BM25: score",
        "Relevant excerpt with **highlighted** keywords.",
        "",
        "CRITICAL: Use markdown **bold** syntax for all important keywords and terms.",
    ],
    markdown=True,
)
