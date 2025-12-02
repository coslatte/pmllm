from pathlib import Path

import pytest

from utils.data_builder import DataBuildConfig, build_data


def test_build_data_runs_conversion_and_prepare(tmp_path, monkeypatch):
    core_src = tmp_path / "core_src"
    derived_src = tmp_path / "derived_src"
    core_src.mkdir()
    derived_src.mkdir()
    output_dir = tmp_path / "out"

    convert_calls = []
    prepare_calls = []

    def fake_convert(src: Path, dst: Path) -> int:
        convert_calls.append((src, dst))
        dst.mkdir(parents=True, exist_ok=True)
        (dst / "sample.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        return 1

    def fake_prepare(**kwargs):
        prepare_calls.append(kwargs)

    monkeypatch.setattr("utils.data_builder.handle_convert", fake_convert)
    monkeypatch.setattr("utils.data_builder.handle_prepare", fake_prepare)

    config = DataBuildConfig(
        core_source=core_src,
        derived_source=derived_src,
        output_dir=output_dir,
        reuse_existing_converted=False,
        sample_fraction=0.5,
    )

    result = build_data(config)

    assert len(convert_calls) == 2
    assert len(prepare_calls) == 1
    assert result.core_converted == 1
    assert not result.core_reused
    assert result.derived_converted == 1
    assert not result.derived_reused
    assert result.headers_dir == output_dir / "core" / "headers"


def test_build_data_reuses_existing_converted(tmp_path, monkeypatch):
    core_src = tmp_path / "core_src"
    derived_src = tmp_path / "derived_src"
    core_src.mkdir()
    derived_src.mkdir()
    output_dir = tmp_path / "out"
    core_target = output_dir / "converted" / "core"
    derived_target = output_dir / "converted" / "derived"
    core_target.mkdir(parents=True)
    derived_target.mkdir(parents=True)
    (core_target / "existing.csv").write_text("a,b", encoding="utf-8")
    (derived_target / "existing.csv").write_text("a,b", encoding="utf-8")

    monkeypatch.setattr(
        "utils.data_builder.handle_convert",
        lambda *_args, **_kwargs: pytest.fail("convert should not run when reusing"),
    )

    prepare_calls: list[dict] = []

    def fake_prepare(**kwargs):
        prepare_calls.append(kwargs)

    monkeypatch.setattr("utils.data_builder.handle_prepare", fake_prepare)

    config = DataBuildConfig(
        core_source=core_src,
        derived_source=derived_src,
        output_dir=output_dir,
        reuse_existing_converted=True,
    )

    result = build_data(config)

    assert result.core_converted == 0
    assert result.core_reused
    assert result.derived_converted == 0
    assert result.derived_reused
    assert len(prepare_calls) == 1
