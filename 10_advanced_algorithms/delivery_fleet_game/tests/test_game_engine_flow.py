import pytest


@pytest.fixture
def greedy_agent(game_engine):
    from src.agents import GreedyAgent

    agent = GreedyAgent(game_engine.delivery_map)
    game_engine.register_agent("greedy_test", agent)
    return agent


def test_start_day_loads_packages(game_engine):
    game_engine.start_day()

    assert game_engine.game_state is not None
    assert len(game_engine.game_state.packages_pending) > 0
    snapshot = game_engine.current_difficulty
    assert snapshot is not None
    assert game_engine.game_state.current_demand_tier == snapshot.demand_tier
    assert snapshot.popularity == game_engine.game_state.popularity_score


def test_execute_day_with_greedy_agent(game_engine, data_loader, greedy_agent):
    game_engine.start_day()

    applied = game_engine.apply_agent_solution("greedy_test")
    assert applied, "Greedy agent should produce a valid plan for tutorial day 1"

    routes = game_engine.game_state.current_routes
    assert routes, "Routes must be present after applying solution"
    for route in routes:
        assert route.is_valid()
        assert route.packages  # No empty routes

    history_before = len(game_engine.game_state.history)
    pending_before = len(game_engine.game_state.packages_pending)

    profit = game_engine.execute_day("greedy_test")
    assert len(game_engine.game_state.history) == history_before + 1
    last_day = game_engine.game_state.history[-1]

    assert last_day.routes_count == len(routes)
    assert last_day.packages_delivered > 0
    assert last_day.packages_delivered <= pending_before
    assert game_engine.game_state.balance == pytest.approx(last_day.balance_end)
    assert profit == last_day.profit
    assert last_day.popularity_end == game_engine.game_state.popularity_score
    assert last_day.demand_tier == game_engine.game_state.current_demand_tier.value
    assert isinstance(last_day.popularity_delta, int)
    assert last_day.penalties >= 0

    # Moving to next day should increment counter and clear routes.
    current_day = game_engine.game_state.current_day
    game_engine.advance_to_next_day()
    assert game_engine.game_state.current_day == current_day + 1
    assert game_engine.game_state.current_routes == []
