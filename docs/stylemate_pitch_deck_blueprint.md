# StyleMate Pitch Deck Blueprint

## Purpose

Create a premium startup pitch deck for `StyleMate` that feels like a continuation of the product itself:

- product-first
- fashion-tech minimal
- calm, editorial, premium
- demo-led, not academic
- AI intelligence presented as product value, not as a research lecture

Target format:

- `10` main slides
- `1` backup slide
- `1920x1080`
- Russian language with selective English product phrases

## Core Story

Deck logic:

1. Problem
2. Solution
3. Demo
4. Intelligence layer
5. Competitive edge
6. Reliability
7. Criteria as proof

Narrative rule:

- first `~70%` of the deck should feel like a real product launch
- last `~30%` should convert product confidence into rational proof

## Visual System

### Mood

- airy
- premium
- monochrome
- fashion + technology
- clean keynote energy

### Style Reference

Source of truth: current `StyleMate` frontend visual language.

Borrow directly:

- `Inter`
- tight, clean headlines
- rounded chips
- translucent white panels
- near-black text
- soft gray secondary text
- black gradient CTA buttons
- soft shadows
- grayscale fashion editorial background

### Palette

- `#111111` for primary text
- soft gray for secondary text
- white and milky-white surfaces
- subtle transparent whites for glass cards
- almost no accent colors

Avoid:

- purple startup gradients
- loud illustration systems
- bright 3D objects
- generic SaaS color coding

### Surface Language

- glass-like cards with soft border
- rounded corners in the `20-32px` range
- soft shadow depth, never harsh
- large negative space
- restrained editorial photography

### Typography

- headline: large, tight, bold, short
- body: short phrases only
- captions: light gray, compact, product-like
- no long paragraphs

## Slide Architecture

### Slide 1. Cover

Title:

`StyleMate`

Subtitle:

`AI outfit assistant`

Support line:

`Подбирает образ из твоего гардероба под конкретную ситуацию`

Composition:

- left: oversized type block
- right: hero product mockup or screenshot
- one glass panel with core value proposition
- grayscale editorial background with soft white blur overlay

Visual goal:

- feel like a premium landing page, not a title slide

### Slide 2. Problem

Title:

`Сложно быстро понять, что надеть`

Content blocks:

- `вещей много, готовых образов мало`
- `каждый сценарий требует другой уместности`
- `decision fatigue даже при полном гардеробе`

Visuals:

- 3 problem cards
- scenario chips like `Date`, `Office`, `Rain`, `Gym`
- tension between many options and no clear answer

### Slide 3. Solution

Title:

`StyleMate превращает гардероб в понятную систему`

Three cards:

- `Цифровой гардероб`
- `Подбор под сценарий`
- `Explanation, почему именно этот outfit`

Visual goal:

- calm, clear, product confidence

### Slide 4. Demo Input

Title:

`Upload. Choose. Generate.`

Need to show:

- upload entry point
- scenario chips
- gender switch
- source switch

Composition:

- one main UI mockup
- 2-3 supporting zoom cards for controls
- input-side product moment

### Slide 5. Demo Output

Title:

`Готовый outfit, а не просто список вещей`

Need to show:

- selected scenario
- output cards
- explanation panel
- finished recommendation state

Priority:

- one of the strongest slides in the deck
- must immediately communicate product value

### Slide 6. How It Works

Title:

`How StyleMate works`

Pipeline:

`User input -> Vision -> Wardrobe understanding -> Rules + RAG -> Outfit result`

Rules:

- maximum `5` blocks
- product-friendly diagram
- no engineering overload

### Slide 7. Why It Is AI

Title:

`Not just UI. Real AI pipeline.`

Core proof points:

- `Local Vision inference`
- `RAG + rules for outfit selection`
- `explanation layer`
- `fallback logic`

Tone:

- intelligence as user value
- no research-paper style explanation

### Slide 8. Why Better Than Alternatives

Title:

`Почему StyleMate сильнее обычных fashion recommendations`

Recommended format:

- 4 comparison cards or a compact premium comparison matrix

Advantage points:

- scenario-based, not generic taste
- gives explanation, not just output
- mixed wardrobe mode
- personal items + shop catalog
- robust with weak requests

### Slide 9. Reliability

Title:

`Built to be robust`

Trust blocks:

- неоднозначные запросы
- конфликтные запросы
- fallback при внешних AI-сбоях
- ручная корректировка vision результата
- изоляция гардероба по пользователю

Tone:

- trust
- stability
- product readiness

### Slide 10. Criteria Proof

Title:

`Why this project scores well`

Table columns:

- `Критерий`
- `Статус`
- `Как закрыт`

Rows:

- `RAG`
- `Local inference`
- `UI / usability`
- `Complex query handling`
- `Personalization`
- `Practical engineering solution`

Footer note:

`Ожидаемая оценка: [editable placeholder]`

Rule:

- compact premium proof slide
- not a huge spreadsheet

### Slide 11. Backup / Q&A

Title:

`Live demo / Q&A`

Content:

- large product visual block
- one strong screenshot or mockup
- footer line: `Upload -> Understand -> Recommend`

## Design System Inside The Deck

### Grid

- `12-column` grid
- generous outer margins
- consistent top rhythm
- asymmetric layouts are allowed, but only within one visual system

### Cards

- translucent white backgrounds
- soft border
- rounded corners
- short copy only
- compact captions in gray

### Buttons and Chips

- reuse product feel from `StyleMate`
- black premium CTA
- white translucent chips
- active chip = dark fill

### Image Language

- grayscale editorial fashion backgrounds
- product mockups with soft shadow
- never use random stock illustrations

## Copy Principles

- one block = one idea
- short confident phrases
- product language first
- mix Russian with selective English terms where it sounds natural
- never academic

Do not use:

- `целью проекта является`
- `в данной работе`
- `в рамках исследования`
- long explanatory paragraphs

## Asset Wishlist

For the strongest final deck, collect these screenshots:

1. Main screen with scenario chips and CTA
2. Wardrobe screen with uploaded items
3. Outfit result screen with explanation
4. Wardrobe item editor modal
5. Optional mixed-mode or empty-state screen

If screenshots are missing:

- use polished mockup compositions
- keep placeholders editable
- stay visually close to real `StyleMate` UI

## Figma Assembly Notes

Recommended file type:

- `Figma Design`, not `Slides`

Reason:

- easier frame control for `1920x1080`
- better freedom for product-style composition
- better fit for MCP inspection flow

Recommended page structure:

- `Deck`
- `Assets`
- `Screenshots`

Frame names:

- `01 Cover`
- `02 Problem`
- `03 Solution`
- `04 Demo Input`
- `05 Demo Output`
- `06 How It Works`
- `07 Real AI`
- `08 Why Better`
- `09 Robust`
- `10 Criteria`
- `11 Backup`

## Current Blocker

To inspect Figma via MCP in this session, a working Figma OAuth token is still needed in the Codex environment. Until that is enabled, this document is the working blueprint and source of truth for the deck structure.
