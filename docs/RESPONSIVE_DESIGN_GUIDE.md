# Responsive Design Guide

## Overview

The current responsive strategy relies on the compiled `static/css/styles.css` bundle plus page-level template styles where needed. Earlier one-off responsive helper stylesheets were archived because they were no longer referenced by the running templates.

## Active Responsive Patterns

- Mobile-first spacing and layout classes from the compiled stylesheet
- Grid stacking for forms on smaller screens
- Homepage hero search that collapses from multi-column desktop layout to vertical mobile layout
- Search and card layouts that remain usable on narrow screens
- Booking flow adjustments that avoid desktop-only assumptions in JavaScript

## Current Breakpoint Direction

- Mobile: stacked layouts, full-width controls, simpler spacing
- Tablet: two-column form and card layouts where appropriate
- Desktop: larger content width, split layouts, richer hero composition

## Areas That Were Improved

- Registration fields now stack correctly on mobile instead of forcing two columns.
- The landing page hero search now adapts cleanly between desktop and mobile.
- Guest browsing flows now work without sign-in interruptions on discovery pages.
- Sale and rent booking states no longer assume the same field set in frontend logic.

## Recommended Next Responsive Pass

- Make the mobile navigation more intentional instead of relying on desktop patterns shrinking down.
- Tighten filter density on small screens so discovery is faster.
- Reduce long vertical stretches on dashboard screens for phones.
- Add more consistent touch target sizing in owner-management areas.
