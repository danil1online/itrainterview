"""Общий помощник банка задач: конструктор словаря одного теста."""


def T(name, stdin, expected_stdout, sample=False):
    return {"name": name, "stdin": stdin, "expected_stdout": expected_stdout, "sample": sample}
