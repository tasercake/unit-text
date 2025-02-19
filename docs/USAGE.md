# unit-text CLI usage

<span style="color: #008000; text-decoration-color: #008000; font-weight: bold">unit-text</span> helps you write unit tests for prose.
It uses ✨ agents ✨ to ensure
that you meet the target audience&#x27;s expectations,
and that your writing achieves the desired outcomes.

**Usage**:

```console
$ unit-text [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `ideate`: Generate ideas for your writing.
* `test`: Test the input file.

## `unit-text ideate`

Generate ideas for your writing.

**Usage**:

```console
$ unit-text ideate [OPTIONS]
```

**Options**:

* `--output PATH`: The output file to write the ideas to.  [default: unit-text.json]
* `--help`: Show this message and exit.

## `unit-text test`

Test the input file.

**Usage**:

```console
$ unit-text test [OPTIONS] FILE
```

**Arguments**:

* `FILE`: [required]

**Options**:

* `--config PATH`: The config file.  [default: unit-text.json]
* `--help`: Show this message and exit.
