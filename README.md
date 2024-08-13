# Laminar AI

This repo provides core for code generation, Laminar CLI, and Laminar SDK.

## Quickstart
```sh
python3 -m venv .myenv
source .myenv/bin/activate  # or use your favorite env management tool

pip install lmnr
```

## Features

- Make Laminar endpoint calls from your Python code
- Make Laminar endpoint calls that can run your own functions as tools
- CLI to generate code from pipelines you build on Laminar or execute your own functions while you test your flows in workshop

## Making Laminar endpoint calls

After you are ready to use your pipeline in your code, deploy it in Laminar following the [docs](https://docs.lmnr.ai/pipeline/run-save-deploy#deploying-a-pipeline-version).

Once your pipeline is deployed, you can call it from Python in just a few lines.

Example use:

```python
from lmnr import Laminar

l = Laminar('<YOUR_PROJECT_API_KEY>')
result = l.run(
    endpoint = 'my_endpoint_name',
    inputs = {'input_node_name': 'some_value'},
    # all environment variables
    env = {'OPENAI_API_KEY': 'sk-some-key'},
    # any metadata to attach to this run's trace
    metadata = {'session_id': 'your_custom_session_id'}
)
```

Resulting in:

```python
>>> result
EndpointRunResponse(
    outputs={'output': {'value': [ChatMessage(role='user', content='hello')]}},
    # useful to locate your trace
    run_id='53b012d5-5759-48a6-a9c5-0011610e3669'
)
```

## Making calls to pipelines that run your own logic

If your pipeline contains tool call nodes, they will be able to call your local code.
The only difference is that you need to pass references
to the functions you want to call right into our SDK.

Example use:

```python
from lmnr import Laminar, NodeInput

# adding **kwargs is safer, in case an LLM produces more arguments than needed
def my_tool(arg1: string, arg2: string, **kwargs) -> NodeInput {
    return f'{arg1}&{arg2}'
}

l = Laminar('<YOUR_PROJECT_API_KEY>')
result = l.run(
    endpoint = 'my_endpoint_name',
    inputs = {'input_node_name': 'some_value'},
    # all environment variables
    env = {'OPENAI_API_KEY': '<YOUR_MODEL_PROVIDER_KEY>'},
    # any metadata to attach to this run's trace
    metadata = {'session_id': 'your_custom_session_id'},
    # specify as many tools as needed.
    # Each tool name must match tool node name in the pipeline
    tools=[my_tool]
)
```

## LaminarRemoteDebugger

If your pipeline contains local call nodes, they will be able to call code right on your machine.

### Step by step instructions to connect to Laminar:

#### 1. Create your pipeline with function call nodes

Add function calls to your pipeline; these are signature definitions of your functions

#### 2. Implement the functions

At the root level, create a file: `pipeline.py`

Annotate functions with the same name.

Example:

```python
from lmnr import Pipeline

lmnr = Pipeline()

@lmnr.func("foo") # the node in the pipeline is called foo and has one parameter arg
def custom_logic(arg: str) -> str:
    return arg * 10
```

#### 3. Link lmnr.ai workshop to your machine

1. At the root level, create a `.env` file if not already
1. In project settings, create or copy a project api key.
1. Add an entry in `.env` with: `LMNR_PROJECT_API_KEY=s0meKey...`
1. In project settings create or copy a dev session. These are your individual sessions.
1. Add an entry in `.env` with: `LMNR_DEV_SESSION_ID=01234567-89ab-cdef-0123-4567890ab`

#### 4. Run the dev environment

```sh
lmnr dev
```

This will start a session, try to persist it, and reload the session on files change.

## CLI for code generation

### Basic usage

```
lmnr pull <pipeline_name> <pipeline_version_name> --project-api-key <PROJECT_API_KEY>
```

Note that `lmnr` CLI command will only be available from within the virtual environment
where you have installed the package.

To import your pipeline
```python
# submodule with the name of your pipeline will be generated in lmnr_engine.pipelines
from lmnr_engine.pipelines.my_custom_pipeline import MyCustomPipeline


pipeline = MyCustomPipeline()
res = pipeline.run(
    inputs={
        "instruction": "Write me a short linkedin post about a dev tool for LLM developers"
    },
    env={
        "OPENAI_API_KEY": <OPENAI_API_KEY>,
    }
)
print(f"Pipeline run result:\n{res}")
```

### Current functionality
- Supports graph generation for graphs with the following nodes: Input, Output, LLM, Router, Code.
- For LLM nodes, it only supports OpenAI and Anthropic models. Structured output in LLM nodes will be supported soon.

## PROJECT_API_KEY

Read more [here](https://docs.lmnr.ai/api-reference/introduction#authentication) on how to get `PROJECT_API_KEY`.
