"""Pruebas propias del inspector."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "starter"))

from inspector import (count_by_kind, find_path, maximum_depth,  # noqa: E402
                       preorder_iterative, preorder_recursive, validate)
from model import Node, Record  # noqa: E402
from sample_data import sample_plant  # noqa: E402


def single_root() -> Node:
    return Node("P1", "plant")


def linear_tree() -> Node:
    return Node("P1", "plant", children=(
        Node("A1", "area", children=(
            Node("M1", "machine", children=(
                Node("S1", "sensor", 1.0),
            )),
        )),
    ))


def branched_tree() -> Node:
    return Node("P1", "plant", children=(
        Node("A1", "area", children=(Node("S1", "sensor", 1), Node("S2", "sensor", 2.5))),
        Node("A2", "area"),
        Node("A3", "area", children=(Node("M1", "machine"),)),
    ))


class ValidateTests(unittest.TestCase):
    def test_valid_trees(self):
        for tree in (single_root(), linear_tree(), branched_tree(), sample_plant()):
            validate(tree)  # no debe lanzar

    def assertInvalid(self, tree):
        with self.assertRaises(ValueError):
            validate(tree)

    def test_empty_name(self):
        self.assertInvalid(Node("   ", "plant"))

    def test_non_text_name(self):
        self.assertInvalid(Node(5, "plant"))

    def test_duplicate_name(self):
        self.assertInvalid(Node("P1", "plant", children=(Node("A1", "area"), Node("A1", "area"))))

    def test_duplicate_name_with_root(self):
        self.assertInvalid(Node("P1", "plant", children=(Node("P1", "area"),)))

    def test_unknown_kind(self):
        self.assertInvalid(Node("P1", "factory"))

    def test_sensor_without_value(self):
        self.assertInvalid(Node("P1", "plant", children=(Node("S1", "sensor"),)))

    def test_sensor_with_bool(self):
        self.assertInvalid(Node("P1", "plant", children=(Node("S1", "sensor", True),)))

    def test_sensor_with_children(self):
        self.assertInvalid(Node("P1", "plant", children=(
            Node("S1", "sensor", 1.0, children=(Node("S2", "sensor", 2.0),)),)))

    def test_non_sensor_with_value(self):
        self.assertInvalid(Node("P1", "plant", 3.0))
        self.assertInvalid(Node("P1", "plant", children=(Node("M1", "machine", 1.0),)))

    def test_error_message_locates_problem(self):
        tree = Node("P1", "plant", children=(Node("A1", "area", children=(Node("S1", "sensor"),)),))
        with self.assertRaises(ValueError) as ctx:
            validate(tree)
        self.assertIn("P1/A1/S1", str(ctx.exception))

    def test_queries_reject_invalid_tree(self):
        bad = Node("P1", "plant", 1.0)
        for func in (preorder_recursive, preorder_iterative, maximum_depth, count_by_kind):
            with self.assertRaises(ValueError):
                func(bad)
        with self.assertRaises(ValueError):
            find_path(bad, "P1")


class PreorderTests(unittest.TestCase):
    def test_sample_paths(self):
        paths = ["/".join(r.path) for r in preorder_recursive(sample_plant())]
        self.assertEqual(paths, ["P1", "P1/A1", "P1/A1/M1", "P1/A1/M1/T1", "P1/A2", "P1/A2/PRES-1"])

    def test_records_content(self):
        records = preorder_recursive(sample_plant())
        self.assertEqual(records[0], Record(("P1",), "plant", None))
        self.assertEqual(records[3], Record(("P1", "A1", "M1", "T1"), "sensor", 21.5))

    def test_single_root(self):
        self.assertEqual(preorder_recursive(single_root()), [Record(("P1",), "plant", None)])

    def test_recursive_equals_iterative(self):
        for tree in (single_root(), linear_tree(), branched_tree(), sample_plant()):
            self.assertEqual(preorder_recursive(tree), preorder_iterative(tree))

    def test_children_order_kept(self):
        names = [r.path[-1] for r in preorder_iterative(branched_tree())]
        self.assertEqual(names, ["P1", "A1", "S1", "S2", "A2", "A3", "M1"])


class QueryTests(unittest.TestCase):
    def test_depth(self):
        self.assertEqual(maximum_depth(single_root()), 1)
        self.assertEqual(maximum_depth(linear_tree()), 4)
        self.assertEqual(maximum_depth(branched_tree()), 3)
        self.assertEqual(maximum_depth(sample_plant()), 4)

    def test_count_by_kind(self):
        self.assertEqual(count_by_kind(single_root()), {"plant": 1})
        self.assertEqual(count_by_kind(sample_plant()),
                         {"plant": 1, "area": 2, "machine": 1, "sensor": 2})
        self.assertNotIn("sensor", count_by_kind(Node("P1", "plant", children=(Node("A1", "area"),))))

    def test_find_root(self):
        self.assertEqual(find_path(sample_plant(), "P1"), ("P1",))

    def test_find_leaf(self):
        self.assertEqual(find_path(sample_plant(), "T1"), ("P1", "A1", "M1", "T1"))
        self.assertEqual(find_path(sample_plant(), "PRES-1"), ("P1", "A2", "PRES-1"))

    def test_find_missing(self):
        self.assertIsNone(find_path(sample_plant(), "X9"))
        self.assertIsNone(find_path(single_root(), "A1"))


class NoMutationTests(unittest.TestCase):
    def test_input_unchanged(self):
        tree = branched_tree()
        before = copy.deepcopy(tree)
        validate(tree)
        preorder_recursive(tree)
        preorder_iterative(tree)
        maximum_depth(tree)
        count_by_kind(tree)
        find_path(tree, "M1")
        self.assertEqual(tree, before)


if __name__ == "__main__":
    unittest.main()
