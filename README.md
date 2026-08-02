# sillybench

Silly benchmarks to test models on.

Every model release ships with a wall of impressive numbers. But everyone uses models so differently — different tasks, different prompts, different taste — that it's impossible to know whether a high score translates to anything in the real world. A model that tops a leaderboard can still be mediocre at *your* thing, and vice versa.

sillybench leans into that. These experiments are not rigorous, not representative, and produce no scores — just small, personal, slightly silly tasks (draw a kookaburra surfing a longboard, rebuild a local website) with each model's raw output kept side by side. Look at the results and decide for yourself. That's the point: the only benchmark that transfers to the real world is running a model on the things you actually do.

## Layout

Each **experiment** is a folder at the repo root:

```
kookaburra-surfing/          <- experiment folder
  prompt.md                  <- the exact prompt used for this experiment
  claude-opus-5.svg          <- model output, named after the model
  deepseek-v4-flash-0731.svg
  inkling-small.svg

peregian-digital-hub/
  prompt.md
  deepseek-v4-flash-0731.html
```

- `prompt.md` records the original prompt (the model implied by the output filename).
- Each model's output is a **single file or folder named after that model** inside the experiment folder. Use a folder instead of a single file when the output is multi-part.

## How to run an experiment

Point a model at the experiment's `prompt.md` and have it perform the work. It should write its output under that experiment's folder as a file/folder named after the model.
