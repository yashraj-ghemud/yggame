# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

from yggame.ai import Action, BehaviorTree, Status
from yggame.dialogue import Choice, DialogueNode, DialogueSession, DialogueTree
from yggame.inventory import Crafting, Inventory, Item, ItemStack, Recipe
from yggame.physics import CollisionGrid, PlatformerBody
from yggame.ui import Button, UIEvent
from yggame.world import AStar, PathRequest


def test_inventory_stacking_and_crafting() -> None:
    ore = Item("ore", "Ore", max_stack=10)
    bar = Item("bar", "Bar", max_stack=5)
    inventory = Inventory(3)
    assert inventory.add(ore, 12) == 12
    assert inventory.count("ore") == 12
    recipe = Recipe("smelt", {"ore": 2}, ItemStack(bar, 1))
    assert Crafting.craft(inventory, recipe)
    assert inventory.count("ore") == 10
    assert inventory.count("bar") == 1


def test_dialogue_condition_and_effect() -> None:
    state = {"has_key": True}
    tree = DialogueTree(
        [
            DialogueNode(
                "start",
                "Guide",
                "Choose",
                choices=(
                    Choice(
                        "Open",
                        "end",
                        condition=lambda values: values["has_key"],
                        effects=(lambda values: values.__setitem__("opened", True),),
                    ),
                ),
            ),
            DialogueNode("end", "Guide", "Done"),
        ],
        "start",
    )
    session = DialogueSession(tree, state=state)
    session.choose(0)
    assert session.current_id == "end"
    assert state["opened"] is True


def test_astar_avoids_blocked_tile() -> None:
    blocked = {(1, 0)}
    path = AStar(lambda x, y: 0 <= x < 4 and 0 <= y < 3 and (x, y) not in blocked).find(
        PathRequest((0, 0), (2, 0))
    )
    assert path is not None
    assert (1, 0) not in path


def test_platformer_jumps_and_lands() -> None:
    grid = CollisionGrid(10, 8, 32)
    for x in range(10):
        grid.set_solid(x, 6)
    body = PlatformerBody(bounds=__import__("yggame").Rect(32, 128, 20, 20))
    for _ in range(120):
        body.update(1 / 60, 0, grid)
    assert body.grounded
    body.request_jump()
    body.update(1 / 60, 0, grid)
    assert body.velocity.y < 0


def test_button_emits_click() -> None:
    button = Button("Play")
    clicked: list[str] = []
    button.on("clicked", lambda _: clicked.append("yes"))
    button.handle(UIEvent("mouse_down", position=__import__("yggame").Vec2(10, 10)))
    button.handle(UIEvent("mouse_up", position=__import__("yggame").Vec2(10, 10)))
    assert clicked == ["yes"]


def test_behavior_tree_action() -> None:
    tree = BehaviorTree(Action(lambda _delta, _blackboard: Status.SUCCESS))
    assert tree.tick(0.1) is Status.SUCCESS
