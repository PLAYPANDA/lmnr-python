from typing import Union

from .utils import is_async
from .types import EvaluatorFunction, ExecutorFunction, EvaluationDatapoint, Numeric
from .laminar import Laminar as L
import asyncio

from abc import ABC, abstractmethod

DEFAULT_BATCH_SIZE = 5


class EvaluationDataset(ABC):
    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def __len__(self) -> int:
        pass

    @abstractmethod
    def __getitem__(self, idx) -> EvaluationDatapoint:
        pass

    def slice(self, start: int, end: int):
        return [self[i] for i in range(max(start, 0), min(end, len(self)))]


class Evaluation:
    def __init__(
        self,
        name,
        data: Union[EvaluationDataset, list[Union[EvaluationDatapoint, dict]]],
        executor: ExecutorFunction,
        evaluators: list[EvaluatorFunction],
        batch_size: int = DEFAULT_BATCH_SIZE,
        project_api_key: str = "",
        base_url: str = "https://api.lmnr.ai",
    ):
        """
        Initializes an instance of the Evaluations class.
        Parameters:
            name (str): The name of the evaluation.
            data (Union[List[Union[EvaluationDatapoint, dict]], EvaluationDataset]): List of data points to evaluate or an evaluation dataset.
                            `data` is the input to the executor function,
                            `target` is the input to the evaluator function.
            executor (Callable[..., Any]): The executor function.
                            Takes the data point + any additional arguments
                            and returns the output to evaluate.
            evaluators (List[Callable[..., Any]]): List of evaluator functions.
                Each evaluator function takes the output of the executor _and_
                the target data, and returns a score. The score can be a
                single number or a record of string keys and number values.
                If the score is a single number, it will be named after the
                evaluator function. If the function is anonymous, it will be
                named `evaluator_${index}`, where index is the index of the
                evaluator function in the list starting from 1.
            batch_size (int, optional): The batch size for evaluation.
                            Defaults to DEFAULT_BATCH_SIZE.
            project_api_key (str, optional): The project API key.
                            Defaults to an empty string.
            base_url (str, optional): The base URL for the LMNR API.
                            Useful if self-hosted elsewhere.
                            Defaults to "https://api.lmnr.ai".
        """

        self.name = name
        self.executor = executor
        self.evaluators = dict(
            zip(
                [
                    (
                        e.__name__
                        if e.__name__ and e.__name__ != "<lambda>"
                        else f"evaluator_{i+1}"
                    )
                    for i, e in enumerate(evaluators)
                ],
                evaluators,
            )
        )
        self.evaluator_names = list(self.evaluators.keys())
        if isinstance(data, list):
            self.data = [
                (
                    EvaluationDatapoint.model_validate(point)
                    if isinstance(point, dict)
                    else point
                )
                for point in data
            ]
        else:
            self.data = data
        self.batch_size = batch_size
        L.initialize(project_api_key=project_api_key, base_url=base_url)

    async def run(self):
        """Runs the evaluation.

        Creates a new evaluation if no evaluation with such name exists, or
        adds data to an existing one otherwise. Evaluates data points in
        batches of `self.batch_size`. The executor
        function is called on each data point to get the output,
        and then evaluate it by each evaluator function.
        """
        response = L.create_evaluation(self.name)

        # Process batches sequentially
        for i in range(0, len(self.data), self.batch_size):
            batch = (
                self.data[i : i + self.batch_size]
                if isinstance(self.data, list)
                else self.data.slice(i, i + self.batch_size)
            )
            try:
                await self._evaluate_batch(batch)
            except Exception as e:
                print(f"Error evaluating batch: {e}")

        try:
            L.update_evaluation_status(response.name, "Finished")
            print(f"Evaluation {response.id} complete")
        except Exception as e:
            print(f"Error updating evaluation status: {e}")

    async def _evaluate_batch(self, batch: list[EvaluationDatapoint]):
        batch_promises = [self._evaluate_datapoint(datapoint) for datapoint in batch]
        results = await asyncio.gather(*batch_promises)

        return L.post_evaluation_results(self.name, results)

    async def _evaluate_datapoint(self, datapoint):
        output = (
            await self.executor(datapoint.data)
            if asyncio.iscoroutinefunction(self.executor)
            else self.executor(datapoint.data)
        )
        target = datapoint.target

        # Iterate over evaluators
        scores = {}
        for evaluator_name in self.evaluator_names:
            evaluator = self.evaluators[evaluator_name]
            value = (
                await evaluator(output, target)
                if asyncio.iscoroutinefunction(evaluator)
                else evaluator(output, target)
            )

            # If evaluator returns a single number, use evaluator name as key
            if isinstance(value, (int, float)):
                scores[evaluator_name] = value
            else:
                scores.update(value)

        return {
            "executorOutput": output,
            "data": datapoint.data,
            "target": target,
            "scores": scores,
        }
