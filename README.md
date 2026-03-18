# StyleMate

StyleMate is an AI outfit assistant that helps users build a relevant look from their wardrobe for a specific scenario.

## What The Product Does

- upload clothing photos
- recognize item category, color, and style with a local vision model
- save items into a digital wardrobe
- generate outfits for scenarios like office, date, rain walk, and gym
- explain why the selected outfit fits the situation
- allow manual correction of recognized item attributes
- support personal wardrobe, shop catalog, and mixed recommendation modes

## Main AI Components

- local vision inference with OpenCLIP `ViT-B-32`
- scenario normalization and prompt-robust rules
- RAG + rule-based outfit selection pipeline
- fallback logic for unstable external services

## Current State

The project includes:

- FastAPI backend
- web frontend
- local vision pipeline
- scenario-aware outfit generation
- user-isolated wardrobes via anonymous owner token
- parser and catalog integration utilities

## Notes

- local user wardrobe data is not meant to be committed
- shop catalog is used as the reusable demo dataset
