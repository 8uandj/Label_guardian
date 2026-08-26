# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React, Vite, TypeScript, Vanilla CSS, FastAPI, PostgreSQL (Supabase), Google Cloud Storage (GCS)

## Users

Perception ML Engineers, Labeling QA Auditors, and Annotators who need to inspect, verify, and correct 3D bounding box annotations on autonomous driving datasets.

## Product Purpose

Label Guardian is a QA platform for 3D perception datasets (autonomous driving). It helps teams audit model predictions against ground truth labels, flag high-risk errors (risk cases), correct bounding boxes, and export production-ready datasets.

## Positioning

An actionable, data-centric QA loop for autonomous driving datasets (like nuScenes and KITTI) that bridges cloud bucket streaming (GCS) with real-time audit interfaces and annotation correction.

## Operating Context

Runs as a central QA checkpoint in ML data pipelines, reading images/point clouds and ground truth labels from GCS buckets, running agentic QA checks, and presenting flagged cases to auditors for verification.

## Capabilities and Constraints

- Read-only real dataset streaming from private GCS buckets (`label_guardian_bucket`).
- Image/Annotation scoping to dataset version (`product`, `v1.0-mini`) and split (`product`, `smoke`).
- Dynamic editing and save-back of 2D/3D annotation coordinates to PostgreSQL (Supabase).
- Live evaluation of frames using model inference and rule checks.

## Brand Commitments

- Visual Identity: Dark theme (Charcoal canvas, Teal brand action, Geist Sans/Mono typography, 4px grid scaling, subtle glassmorphism).
- Color Archetype: Dark tech/developer tool.
- Logos and Icons: Lucide icon set.

## Evidence on Hand

- Frontend workspace, overview dashboard, reports page, and settings view fully integrated with API.
- Live database connection and GCS bucket access tested.
- 156 backend tests and 34 frontend tests passing.

## Product Principles

1. **Precision & Scannability**: UI is dark and neutral so visual annotations (3D bounding boxes) and semantic badges retain clear meaning.
2. **Operational Silence**: Clear, focused workspace layouts optimized for repetitive reviewer tasks.
3. **No Placeholders**: All data displays are backed by real database records or real GCP assets.
