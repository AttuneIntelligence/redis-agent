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

Designing cognitive architectures capable of agency is a notoriously difficult task. Base language models are confined to the knowledge of their training, and retrieval-augmented generation (RAG) pipelines generally follow a rigid pipeline for execution.

`Redis-Agent` leverages Chain-of-Thought reasoning to generate a plan of action for complex questions, and then offloads the task of function calling to a queue of Redis workers for concurrent execution.

Created and maintained by _[Reed Bender](https://github.com/mrbende)_.

<div align="center">
  <img src="assets/RedisAgentSchema.png" alt="Redis Agent Schema" />
</div>

---

# Getting Started

## Step 1: Install Docker
  Install [Docker](https://docs.docker.com/get-docker/) on your machine if it is not already installed.

## Step 2: Compile API Keys
1. _**[OpenAI Key](https://platform.openai.com/api-keys)**_ 
    - OpenAI 
2. _**[SerpAPI Key](https://serpapi.com/dashboard)**_ (*optional*)
    - This key connects to SerpAPI, which enables web search function calling.
2. _**[Pubmed Key](https://account.ncbi.nlm.nih.gov/settings/)**_ (*optional*)
    - This key connects to Pubmed, connecting the agent to published biomedical literature.

Once each of these keys has been acquired (or only the OpenAI key to launch with a subset of available functions), the installation and deployment can be executed.

Create a `.env` file at `server/.env` to provide authentification to the locally deployed application.

```bash
OPENAI_API_KEY=""

### SERPAPI AUTH   (optional)
SERPAPI_API_KEY=""

### PUBMED API AUTH   (optional)
PUBMED_EMAIL="user@email.com"
PUBMED_API_KEY=""
```

## Step 3: Deployment

```bash
### START
docker-compose up --build
```

This will launch the application on your local machine, available at _[http://localhost:3000](http://localhost:3000)_.

---

# Features

`Redis-Agent` integrates a [Redis Queue](https://redis.io/glossary/redis-queue/) to offload the execution of function calls to collection of workers in a first-in-first-out schema, leaving the primary Flask server free to process user requests. This allows for concurrent execution of multiple functions, reducing the time to first token generation of the streamed LLM response while executing multiple functions in parallel.

Prior to employing the agent workers, the user's question is sent to GPT to generate a sequential plan of action with Chain-of-Thought reasoning, defining a logical series of function queries to pull source-referenced information to support the response generation.

Chat history for the user's conversation is maintained in the Redis container, summarizing the chat thread with each iteration to fit within the LLM's context window limit while maintaining conversational context.

The application client is a simple NextJS + React chat interface, deployed to localhost for self-hosted interaction. The complete technical stack can also be deployed to a production application server with minimal changes.  

## Available Functions

The default tools available to the `Redis-Agent` system work together to inform ChatGPT's response with source-referenced supplemental information. The following tools are available to the deployed agent:
    * [Pubmed](https://pubmed.ncbi.nlm.nih.gov/)
        - Access peer-reviewed clinical and biomedical research literature.
    * [ClinicalTrials.gov](https://clinicaltrials.gov/)
        - Access current clinical trials from arround the world.
    * [arXiv](https://arxiv.org/)
        - Access literature regarding physics, mathematics, computer science, and quantitative biology.
    * [US Patent & Trademark Office](https://www.uspto.gov/patents/search)
        - Access granted and submitted patents from the USPTO.
    * [Neurips](https://proceedings.neurips.cc/)
        - Access proceedings from the Neural Information Processing Systems conference.
    * [Github](https://github.com/dashboard)
        - Access source code repositories.
    * [Google Scholars Profile](https://scholar.google.com/intl/en/scholar/citations.html)
        - Access the scholar profile for any individual's academic research publications.
    * [Google Search](https://www.google.com/webhp)
        - Access the complete internet.

These functions work together as an integrated pool of source information available to the deployed digital agent.