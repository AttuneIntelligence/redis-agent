<div align="center">
    <h1>Redis Agent</h1>
    <a href="https://github.com/attuneintelligence/redis-agent/actions">
      <img src="https://github.com/attuneintelligence/redis-agent/actions/workflows/main.yml/badge.svg" alt="Build Status" />
    </a>
    <a href="https://github.com/attuneintelligence/redis-agent">
      <img src="https://img.shields.io/github/stars/attuneintelligence/redis-agent?style=social" alt="Stars" />
    </a>
    <a href="https://github.com/attuneintelligence/redis-agent/issues">
      <img src="https://img.shields.io/github/issues/attuneintelligence/redis-agent" alt="Stars" />
    </a>
    <a href="https://github.com/attuneintelligence/redis-agent/blob/main/LICENSE">
      <img src="https://img.shields.io/github/license/attuneintelligence/redis-agent" alt="License" />
    </a>
    <a href="https://twitter.com/reedbndr">
      <img src="https://img.shields.io/twitter/follow/reedbndr?style=social" alt="License" />
    </a>
    <hr>
    <!-- <blockquote>“Such is my task. I go to gather this, the sacred knowledge, here and there dispersed about the world, long lost or never found.”<br>- <i>Browning's Paracelsus</i></blockquote> -->
    <blockquote>“Intelligence is a fixed goal with variable means of achieving it.”<br><i>-William James</i></blockquote>
    <br>
</div>

Designing cognitive architectures capable of agency is a notoriously difficult task. Base language models are confined to the knowledge of their training, and retrieval-augmented generation (RAG) pipelines generally follow a rigid pipeline with predefined source knowledge.

`Redis-Agent` leverages Chain-of-Thought reasoning to generate a plan for responding to complex questions, and then offloads the task of function calling to a queue of Redis workers.

<div align="center">
  <img src="assets/RedisAgentSchema.png" alt="Redis Agent Schema" />
</div>

---

# Local Deployment

```bash
### START
docker-compose up --build

### STOP
docker-compose down
```

---