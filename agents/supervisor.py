"""Langgraph supervisor agent for orchestrating stock research."""

from typing import Any, Literal, TypedDict
import operator

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import structlog

from agents.market_sentiment import MarketSentimentAgent
from agents.stock_research import StockResearchAgent
from agents.investor_tracking import InvestorTrackingAgent
from agents.analysis_engine import AnalysisEngineAgent

logger = structlog.get_logger(__name__)


class AgentState(TypedDict):
    """State passed between agents in the workflow."""
    messages: list[BaseMessage]
    ticker: str | None
    task_type: str
    current_agent: str | None
    results: dict[str, Any]
    error: str | None
    iteration: int
    max_iterations: int


class SupervisorAgent:
    """Supervisor agent that orchestrates specialized sub-agents."""

    def __init__(self) -> None:
        self.market_agent = MarketSentimentAgent()
        self.research_agent = StockResearchAgent()
        self.investor_agent = InvestorTrackingAgent()
        self.analysis_agent = AnalysisEngineAgent()

        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the agent workflow graph."""
        workflow = StateGraph(AgentState)

        # Add nodes for each agent
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("market_sentiment", self._market_sentiment_node)
        workflow.add_node("stock_research", self._stock_research_node)
        workflow.add_node("investor_tracking", self._investor_tracking_node)
        workflow.add_node("analysis_engine", self._analysis_engine_node)
        workflow.add_node("aggregate", self._aggregate_node)

        # Set entry point
        workflow.set_entry_point("supervisor")

        # Add conditional edges from supervisor
        workflow.add_conditional_edges(
            "supervisor",
            self._route_task,
            {
                "market_sentiment": "market_sentiment",
                "stock_research": "stock_research",
                "investor_tracking": "investor_tracking",
                "analysis_engine": "analysis_engine",
                "aggregate": "aggregate",
                "end": END,
            },
        )

        # All agents return to supervisor for next routing decision
        workflow.add_edge("market_sentiment", "supervisor")
        workflow.add_edge("stock_research", "supervisor")
        workflow.add_edge("investor_tracking", "supervisor")
        workflow.add_edge("analysis_engine", "supervisor")
        workflow.add_edge("aggregate", END)

        return workflow.compile()

    def _supervisor_node(self, state: AgentState) -> AgentState:
        """Supervisor decides which agent to run next."""
        task_type = state["task_type"]
        results = state["results"]
        iteration = state["iteration"]

        logger.info(
            "Supervisor routing",
            task_type=task_type,
            iteration=iteration,
            completed=list(results.keys()),
        )

        # Increment iteration
        state["iteration"] = iteration + 1

        # Check max iterations
        if state["iteration"] > state["max_iterations"]:
            state["current_agent"] = "aggregate"
            return state

        # Route based on task type and what's completed
        if task_type == "full_research":
            # Full research workflow
            if "market_data" not in results:
                state["current_agent"] = "market_sentiment"
            elif "stock_data" not in results:
                state["current_agent"] = "stock_research"
            elif "fund_data" not in results:
                state["current_agent"] = "investor_tracking"
            elif "analysis" not in results:
                state["current_agent"] = "analysis_engine"
            else:
                state["current_agent"] = "aggregate"

        elif task_type == "market_sentiment":
            if "market_data" not in results:
                state["current_agent"] = "market_sentiment"
            else:
                state["current_agent"] = "aggregate"

        elif task_type == "stock_analysis":
            if "stock_data" not in results:
                state["current_agent"] = "stock_research"
            elif "analysis" not in results:
                state["current_agent"] = "analysis_engine"
            else:
                state["current_agent"] = "aggregate"

        elif task_type == "fund_tracking":
            if "fund_data" not in results:
                state["current_agent"] = "investor_tracking"
            else:
                state["current_agent"] = "aggregate"

        else:
            state["current_agent"] = "end"

        return state

    def _route_task(self, state: AgentState) -> str:
        """Route to the appropriate agent based on state."""
        return state["current_agent"] or "end"

    async def _market_sentiment_node(self, state: AgentState) -> AgentState:
        """Run market sentiment analysis."""
        try:
            result = await self.market_agent.analyze()
            state["results"]["market_data"] = result
            state["messages"].append(
                AIMessage(content=f"Market sentiment analysis completed: {result.get('overall_sentiment', 'N/A')}")
            )
        except Exception as e:
            logger.error("Market sentiment agent failed", error=str(e))
            state["error"] = str(e)
            state["results"]["market_data"] = {"error": str(e)}

        return state

    async def _stock_research_node(self, state: AgentState) -> AgentState:
        """Run stock research data collection."""
        ticker = state.get("ticker")
        if not ticker:
            state["error"] = "No ticker specified for stock research"
            return state

        try:
            result = await self.research_agent.research(ticker)
            state["results"]["stock_data"] = result
            state["messages"].append(
                AIMessage(content=f"Stock research completed for {ticker}")
            )
        except Exception as e:
            logger.error("Stock research agent failed", ticker=ticker, error=str(e))
            state["error"] = str(e)
            state["results"]["stock_data"] = {"error": str(e)}

        return state

    async def _investor_tracking_node(self, state: AgentState) -> AgentState:
        """Run investor/fund tracking."""
        ticker = state.get("ticker")

        try:
            result = await self.investor_agent.track(ticker)
            state["results"]["fund_data"] = result
            state["messages"].append(
                AIMessage(content=f"Fund tracking completed, found {len(result.get('funds', []))} funds")
            )
        except Exception as e:
            logger.error("Investor tracking agent failed", error=str(e))
            state["error"] = str(e)
            state["results"]["fund_data"] = {"error": str(e)}

        return state

    async def _analysis_engine_node(self, state: AgentState) -> AgentState:
        """Run comprehensive analysis."""
        try:
            result = await self.analysis_agent.analyze(
                ticker=state.get("ticker"),
                stock_data=state["results"].get("stock_data", {}),
                market_data=state["results"].get("market_data", {}),
                fund_data=state["results"].get("fund_data", {}),
            )
            state["results"]["analysis"] = result
            state["messages"].append(
                AIMessage(content=f"Analysis completed: {result.get('recommendation', 'N/A')}")
            )
        except Exception as e:
            logger.error("Analysis engine agent failed", error=str(e))
            state["error"] = str(e)
            state["results"]["analysis"] = {"error": str(e)}

        return state

    def _aggregate_node(self, state: AgentState) -> AgentState:
        """Aggregate all results into final output."""
        results = state["results"]

        # Create summary
        summary = {
            "ticker": state.get("ticker"),
            "task_type": state["task_type"],
            "iterations": state["iteration"],
            "success": state["error"] is None,
            "error": state["error"],
        }

        # Add individual results
        if "market_data" in results:
            summary["market_sentiment"] = results["market_data"].get("overall_sentiment")

        if "stock_data" in results:
            summary["current_price"] = results["stock_data"].get("current_price")
            summary["company_name"] = results["stock_data"].get("company_name")

        if "fund_data" in results:
            summary["fund_count"] = len(results["fund_data"].get("funds", []))

        if "analysis" in results:
            summary["recommendation"] = results["analysis"].get("recommendation")
            summary["confidence"] = results["analysis"].get("confidence_score")
            summary["target_price"] = results["analysis"].get("target_price_6m")

        state["results"]["summary"] = summary
        state["messages"].append(
            AIMessage(content=f"Research completed: {summary}")
        )

        return state

    async def run(
        self,
        task_type: str,
        ticker: str | None = None,
        max_iterations: int = 10,
    ) -> dict[str, Any]:
        """Run the supervisor workflow.

        Args:
            task_type: Type of task (full_research, market_sentiment, stock_analysis, fund_tracking)
            ticker: Stock ticker for stock-related tasks
            max_iterations: Maximum number of agent iterations

        Returns:
            Workflow results
        """
        initial_state: AgentState = {
            "messages": [HumanMessage(content=f"Execute {task_type} for {ticker or 'market'}")],
            "ticker": ticker,
            "task_type": task_type,
            "current_agent": None,
            "results": {},
            "error": None,
            "iteration": 0,
            "max_iterations": max_iterations,
        }

        logger.info("Starting supervisor workflow", task_type=task_type, ticker=ticker)

        # Run the graph
        final_state = await self.graph.ainvoke(initial_state)

        logger.info(
            "Supervisor workflow completed",
            iterations=final_state["iteration"],
            success=final_state["error"] is None,
        )

        return final_state["results"]


# Convenience functions
async def run_full_research(ticker: str) -> dict[str, Any]:
    """Run full stock research workflow."""
    supervisor = SupervisorAgent()
    return await supervisor.run("full_research", ticker)


async def run_market_sentiment() -> dict[str, Any]:
    """Run market sentiment analysis."""
    supervisor = SupervisorAgent()
    return await supervisor.run("market_sentiment")


async def run_stock_analysis(ticker: str) -> dict[str, Any]:
    """Run stock analysis workflow."""
    supervisor = SupervisorAgent()
    return await supervisor.run("stock_analysis", ticker)


async def run_fund_tracking(ticker: str | None = None) -> dict[str, Any]:
    """Run fund tracking workflow."""
    supervisor = SupervisorAgent()
    return await supervisor.run("fund_tracking", ticker)
