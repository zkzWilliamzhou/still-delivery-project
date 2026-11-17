"""First implementation of total, deliberately written as an explicit loop."""


def total(values):
    accumulator = 0
    for value in values:
        accumulator += value
    return accumulator
