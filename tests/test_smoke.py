"""Smoke tests for the BigP3 ALS analysis package."""


def test_package_exposes_version() -> None:
    import bigp3_als

    assert bigp3_als.__version__ == "0.1.0"
