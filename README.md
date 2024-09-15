# Laminar Python

OpenTelemetry log sender for [Laminar](https://github.com/lmnr-ai/lmnr) for Python code.

 <a href="https://pypi.org/project/lmnr/"> ![PyPI - Version](https://img.shields.io/pypi/v/lmnr?label=lmnr&logo=pypi&logoColor=3775A9) </a>
![PyPI - Downloads](https://img.shields.io/pypi/dm/lmnr)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/lmnr)



## Quickstart

First, install the package:

```sh
python3 -m venv .myenv
source .myenv/bin/activate  # or use your favorite env management tool

pip install lmnr
```

Then, you can initialize Laminar in your main file and instrument your code.

```python
import os
from openai import OpenAI
from lmnr import Laminar as L, Instruments, observe

L.initialize(project_api_key=os.environ["LMNR_PROJECT_API_KEY"], instruments={Instruments.OPENAI})

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def poem_writer(topic: str):
    prompt = f"write a poem about {topic}"
    # OpenAI calls are automatically instrumented
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
    )
    poem = response.choices[0].message.content
    return poem

@observe() # annotate all functions you want to trace
def handle_user_request(...):
    ...

    poem = poem_writer(topic="laminar flow")
    
    ...
```

Note that you need to only initialize Laminar once in your application.

### Project API key

Get the key from the settings page of your Laminar project ([Learn more](https://docs.lmnr.ai/api-reference/introduction#authentication)).
You can either pass it to `.initialize()` or set it to `.env` at the root of your package with the key `LMNR_PROJECT_API_KEY`.

## Instrumentation

### Manual instrumentation

We provide a simple `@observe()` decorator, to trace various functions in your code.

Also, you can use `Laminar.start_as_current_span` if you want to record a chunk of your code using `with` statement.

```python
import os
from openai import OpenAI
from lmnr import Laminar as L, Instruments

L.initialize(project_api_key=os.environ["LMNR_PROJECT_API_KEY"], instruments={Instruments.OPENAI})

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def poem_writer(topic: str):
    prompt = f"write a poem about {topic}"
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt},
    ]

    # OpenAI calls are still automatically instrumented
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )
    poem = response.choices[0].message.content

    return poem

def handle_user_request(...):
    with L.start_as_current_span(name="poem_writer", input=messages):
        ...

        poem = poem_writer(topic="laminar flow")
        
        ...
        
        # while within the span, you can attach laminar events to it
        L.event("is_poem_generated", True)

        L.set_span_output(poem)
```

### Automatic instrumentation

If you want to automatically instrument particular LLM, Vector DB, or other
calls with OpenTelemetry-compatible instrumentation, then pass the appropriate instruments to `.initialize()`.

You can pass an empty set as `instruments=set()` to disable any kind of automatic instrumentation. 
Also if you want to automatically instrument all supported libraries, then pass `instruments=None` or don't pass `instruments` at all.

Check [autoinstrumentable libraries](#autoinstrumentable-libraries) section to see the list of supported libraries.

## Sending events

You can send events in two ways:
- `.event(name, value)` – for a pre-defined event with one of possible values.
- `.evaluate_event(name, evaluator, data)` – for an event that is evaluated by evaluator pipeline based on the data.

Note that to run an evaluate event, you need to crate an evaluator pipeline and create a target version for it.

Read our [docs](https://docs.lmnr.ai) to learn more about event types and how they are created and evaluated.

### Example

```python
from lmnr import Laminar as L
# ...
poem = response.choices[0].message.content

# this will register True or False value with Laminar
L.event("topic alignment", topic in poem)

# this will run the pipeline `check_wordy` with `poem` set as the value
# of `text_input` node, and write the result as an event with name
# "excessive_wordiness"
L.evaluate_event("excessive_wordiness", "check_wordy", {"text_input": poem})
```

## Laminar pipelines as prompt chain managers

You can create Laminar pipelines in the UI and manage chains of LLM calls there.

After you are ready to use your pipeline in your code, deploy it in Laminar by selecting the target version for the pipeline.

Once your pipeline target is set, you can call it from Python in just a few lines.

Example use:

```python
from lmnr import Laminar as L

L.initialize('<YOUR_PROJECT_API_KEY>', instruments=set())

result = l.run(
    pipeline = 'my_pipeline_name',
    inputs = {'input_node_name': 'some_value'},
    # all environment variables
    env = {'OPENAI_API_KEY': 'sk-some-key'},
)
```

Resulting in:

```python
>>> result
PipelineRunResponse(
    outputs={'output': {'value': [ChatMessage(role='user', content='hello')]}},
    # useful to locate your trace
    run_id='53b012d5-5759-48a6-a9c5-0011610e3669'
)
```

## Running offline evaluations on your data

You can evaluate your code with your own data and send it to Laminar using the `Evaluation` class.

Evaluation takes in the following parameters:
- `name` – the name of your evaluation. If no such evaluation exists in the project, it will be created. Otherwise, data will be pushed to the existing evaluation
- `data` – an array of `EvaluationDatapoint` objects, where each `EvaluationDatapoint` has two keys: `target` and `data`, each containing a key-value object. Alternatively, you can pass in dictionaries, and we will instantiate `EvaluationDatapoint`s with pydantic if possible
- `executor` – the logic you want to evaluate. This function must take `data` as the first argument, and produce any output. *
- `evaluators` – evaluaton logic. List of functions that take output of executor as the first argument, `target` as the second argument and produce a numeric scores. Each function can produce either a single number or `dict[str, int|float]` of scores.

\* If you already have the outputs of executors you want to evaluate, you can specify the executor as an identity function, that takes in `data` and returns only needed value(s) from it.

### Example

```python
from openai import AsyncOpenAI
import asyncio
import os

openai_client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

async def get_capital(data):
    country = data["country"]
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": f"What is the capital of {country}? Just name the "
                "city and nothing else",
            },
        ],
    )
    return response.choices[0].message.content.strip()


# Evaluation data
data = [
    {"data": {"country": "Canada"}, "target": {"capital": "Ottawa"}},
    {"data": {"country": "Germany"}, "target": {"capital": "Berlin"}},
    {"data": {"country": "Tanzania"}, "target": {"capital": "Dodoma"}},
]


def evaluator_A(output, target):
    return 1 if output == target["capital"] else 0


# Create an Evaluation instance
e = Evaluation(
    name="py-evaluation-async",
    data=data,
    executor=get_capital,
    evaluators=[evaluator_A],
    project_api_key=os.environ["LMNR_PROJECT_API_KEY"],
)

# Run the evaluation
asyncio.run(e.run())
```

## Autoinstrumentable libraries

Currently, autoinstrumentation for the following libraries is supported:

- OpenAI
- Anthropic
- Cohere
- Pinecone
- Chroma
- Google GenerativeAI
- LangChain
- Mistral
- Ollama
- LlamaIndex
- Milvus
- Transformers
- Together
- Redis
- Requests
- Urllib3
- PyMySQL
- Bedrock
- Replicate
- VertexAI
- WatsonX
- Weaviate
- Aleph Alpha
- Marqo
- LanceDB

Thanks to Traceloop for implementing autoinstrumentation for most of the libraries listed above.

## Acknowledgements

This repository uses the code from and is inspired by [OpenLLMetry](https://github.com/traceloop/openllmetry), open-source package
by TraceLoop.
