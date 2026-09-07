"""
Shared utilities for CrewAI projects.
"""

from crewai import Agent, Task, Crew, Process


def build_crew(agents: list, tasks: list, verbose: bool = True, process=Process.hierarchical) -> Crew:
    return Crew(agents=agents, tasks=tasks, verbose=verbose, process=process)


def make_agent(role: str, goal: str, backstory: str, tools: list = None, llm=None) -> Agent:
    return Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        tools=tools or [],
        llm=llm,
        verbose=False,
        allow_delegation=True,
    )


def make_task(description: str, agent: Agent, expected_output: str = "A comprehensive summary") -> Task:
    return Task(description=description, agent=agent, expected_output=expected_output)
