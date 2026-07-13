from __future__ import annotations

import hashlib

from player_data_contracts import content_hash


def test_content_hash_matches_sorted_filename_digest_pairs() -> None:
    file_hashes = {
        "players.csv": "b" * 64,
        "player_attributes.csv": "a" * 64,
    }
    expected_payload = f"player_attributes.csv:{'a' * 64}\nplayers.csv:{'b' * 64}"

    assert content_hash(file_hashes) == hashlib.sha256(expected_payload.encode("utf-8")).hexdigest()
    assert tuple(file_hashes) == ("players.csv", "player_attributes.csv")


def test_content_hash_is_independent_of_mapping_insertion_order() -> None:
    first = {"b.csv": "2" * 64, "a.csv": "1" * 64}
    second = {"a.csv": "1" * 64, "b.csv": "2" * 64}

    assert content_hash(first) == content_hash(second)


def test_empty_content_hash_is_sha256_of_empty_input() -> None:
    assert content_hash({}) == hashlib.sha256(b"").hexdigest()
