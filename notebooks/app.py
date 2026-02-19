import marimo

__generated_with = "0.10.12"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md("Hello")
    return (mo,)


@app.cell
def test_cell():
    from utils import add

    assert add(1, 2) == 3
    assert add(0, 0) == 0
    assert add(-1, 1) == 0
    return


if __name__ == "__main__":
    app.run()
