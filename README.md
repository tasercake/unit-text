<h1 align="center">unit-text</h1>
<h3 align="center">Unit tests for plain text</h3>

<p align="center">
    <a  href="https://pypi.org/project/unit-text/">
        <img alt="CI" src="https://img.shields.io/pypi/v/unit-text.svg?style=flat-round&logo=pypi&logoColor=white">
    </a>
</p>

<div align="center">

![unit-text logo](./docs/img/logo.png)

</div>

---

Don't let LLMs write blog posts for you. Do your research, bring your own voice,
and use LLMs to criticise and iterate on your writing.

## Why unit-text?

If you're a developer like us:

- You're probably aware you should write more (either because your leadership asks for it,
  or because you'd like to be invited as a conference speaker, or <insert your own reason here>...)
- You don't know what to write about.
- You have considered letting ChatGPT write blog posts for you.

If you tried the last option (or read anything on the Internet in the past 2 years)
you would also know why it's not really that good of an idea.

Sure, you may get a perfectly good post, but it won't be your own.

`unit-text` applies the concept of unit tests to prose. You are the one writing, the LLM is just your critic.

First, you define a goal, the audience you have in mind,
and what you wanted them to do differently after they read your post.
Then, you start writing and iterating on your draft. `unit-text` gives you feedback: you run _tests_
to validate whether your draft is going in the right direction.

An AI copy editor, you could say.

## Usage

### Requirements

Either:

- [Ollama](https://ollama.com) must be running locally;
- `OLLAMA_HOST` should point to an Ollama server.

```bash
# To generate a blog idea
unit-text ideate

# To validate the working draft
unit-text test <path-to-the-draft>
```
