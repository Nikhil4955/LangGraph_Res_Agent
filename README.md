# Restaurant Order Agent

I have built this project keeping in mind that the user gets **3 attempts for
ordering**. If the selected dish is unavailable, the requested quantity is too
large, or the kitchen cannot prepare the dish, the order attempt is counted and
the user can try another order. After 3 failed order attempts, the process is
terminated.

The same idea applies to serving. If the `serve` tool fails, the workflow sends
the order back to the kitchen and tries to serve it again. Serving is attempted
up to 3 times. If all 3 serving attempts fail, the current order is canceled,
the user is asked to select a completely new dish, and an order attempt is
counted.

When the food is successfully served, the process ends and the user sees:

```text
The serve has been done. Thank you!
```

## Project Explanation

This project is a restaurant ordering agent built with LangGraph. It uses a
state graph to control the order from selection to serving:

1. The user sees the menu in a table with a number, dish name, price, and
	quantity available.
2. The user enters the number of a dish and then enters the desired quantity.
3. `take_order` checks that the dish exists and that enough portions are
	available.
4. `cook` prepares the requested dish.
5. `serve` delivers the dish to the user.
6. Conditional graph edges decide whether to continue, retry, request a new
	order, or terminate the process.

The graph state uses `typing.Annotated` with `operator.add` so that
`order_attempts` and `serve_retries` accumulate across workflow nodes.

The agent also strictly rejects unrelated questions. A request that does not
contain a structured restaurant order is ended with the termination sequence:

```text
TERMINATE: I can only help with restaurant orders.
```

## Project Files

- `agenter.py` contains the menu, order tools, LangGraph workflow, retry logic,
  and interactive command-line interface.
- `test_agenter.py` contains five tests for rejected input, failed orders,
  cooking failures, and serving failures.
- `pyproject.toml` contains the project metadata and LangGraph dependency.

## Setup

Clone the project directly from GitHub into a local folder.

```powershell
git clone https://github.com/Nikhil4955/LangGraph_Res_Agent.git 
```

### Install `uv`

On Windows, install `uv` with PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Restart the terminal if necessary, then confirm that it is installed:

```powershell
uv --version
```

### Create the virtual environment

Create a project virtual environment:

```powershell
uv venv
```

Activate it in PowerShell if you want to use it directly:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Install dependencies

Install the dependencies declared by the project:

```powershell
uv sync
```

The project requires LangGraph. If you are creating the project from an empty
folder, you can add it with:

```powershell
uv add langgraph
```

`operator` is part of Python's standard library, so it does not need to be
installed separately. It is imported by `agenter.py` for the annotated state
reducers.

## Run the Agent

Start the interactive restaurant agent with:

```powershell
uv run python .\agenter.py
```

The program displays the numbered menu. Enter the number of the dish you want,
then enter its quantity. If the order fails, the program allows another order
until the maximum of 3 order attempts is reached.

## Run the Tests

Run the workflow tests with:

```powershell
uv run python -m unittest -v .\test_agenter.py
```

The test file verifies:

- unrelated human queries are rejected;
- incomplete restaurant requests are rejected;
- an unavailable order can be followed by another order;
- cooking failures increase the order-attempt count; and
- serving failures retry up to 3 times before requesting a new dish.
