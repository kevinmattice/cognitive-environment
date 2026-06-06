---
type: Note
status: Active
related_to:
  - "[[CCE]]"
  - "[[Atlas]]"
  - "[[District Structure Proposal]]"
  - "[[Cognitive Environment Atlas]]"
---

# How to Read This Atlas

This vault is a map of a big project.

It is not the whole project itself. It is a way to see the important parts, what kind of things they are, and how they connect.

## The simple picture

Think of [[CCE]] as the whole city.

Think of [[Atlas]] as the map of that city.

Think of each entity note as a landmark on the map.

Think of the relationship fields as the roads between landmarks.

## What the main parts are

[[CCE]] is the whole environment. It is the biggest container in this atlas.

[[Atlas]] is the representation of [[CCE]]. It is the thing that makes the environment easier to inspect and navigate.

[[Cognitive Environment Atlas]] is the note that explains the purpose of the atlas itself. It says this vault is meant to make the environment legible to both humans and agents.

[[District Structure Proposal]] is a helper note. It suggests an easier reading layout by grouping the landmarks into three districts:

- Atlas Layer: knowledge and records such as [[Corpus]], [[Memory]], [[Provenance]], and [[Cognitive Registry]]
- Interaction Layer: tools and interfaces such as [[Tolaria]], [[Codex]], [[ChatGPT]], and [[GitHub]]
- Runtime Layer: systems and infrastructure such as [[PEM]], [[Matrix]], [[Colossus]], [[Element]], and [[Browser Agents]]

## How to read a note

When you open a note, read it in this order:

1. Look at the `type` property. That tells you what kind of thing it is, like a `System`, `Artifact`, `Interface`, or `Person`.
2. Look at relationship properties such as `belongs_to`, `contains`, `related_to`, `uses`, `has`, or `represents`. Those tell you how the note connects to other notes.
3. Read the short body text. That gives the plain-language meaning of the thing.

## What the relationships mean

The important idea in Tolaria is that meaning comes more from relationships than from folders.

- `belongs_to` means this thing lives inside a bigger thing
- `contains` means this thing includes other things
- `represents` means one note models or stands for another thing
- `related_to` means two things are connected, even if the exact relationship is still loose
- `uses`, `has`, and `governs` give more specific links when we know the role clearly

## How the pieces connect

At the top is [[CCE]].

Inside [[CCE]] are major parts like [[PEM]], [[Matrix]], and [[Atlas]].

[[Atlas]] is the knowledge-facing map of [[CCE]], and the other entity notes fill in the important landmarks around it.

The interface notes such as [[Tolaria]] and [[Codex]] are how a person or an agent interacts with the map.

The runtime and infrastructure notes such as [[PEM]], [[Matrix]], [[Colossus]], and [[Element]] describe the systems that make the larger environment work.

The knowledge-oriented notes such as [[Corpus]], [[Memory]], [[Provenance]], and [[Cognitive Registry]] describe the information, records, and capabilities that make the atlas useful.

## The goal of this vault

The goal is not to capture everything at once.

The goal is to create a readable world-model that helps you answer questions like:

- What exists in this project?
- What kind of thing is it?
- What larger thing does it belong to?
- What other things does it connect to?

If this note is doing its job, you should be able to start at [[CCE]], follow links outward, and slowly build a mental picture of the whole environment without getting lost.
