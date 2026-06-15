---
name: daisyui-frontend
description: Design UIs using daisyUI component classes with Tailwind CSS. Use when building frontends, creating forms, modals, cards, navbars, alerts, or when the user mentions daisyUI, Tailwind components, or UI design with semantic component classes.
---

# daisyUI Frontend Design

## Core Principles

daisyUI provides semantic component class names that abstract Tailwind utilities. Use daisyUI for UI parts (btn, card, modal) and Tailwind for layout, spacing, and customization. daisyUI is a Tailwind plugin—always pair with Tailwind.

**Class usage**: Always start with the base component class (e.g. `btn`), then add modifiers (e.g. `btn-primary`, `btn-lg`).

## Setup

Ensure Tailwind config includes daisyUI:

```js
plugins: [require("daisyui")],
daisyui: {
  themes: ["light", "dark"],
},
```

For themes, see [daisyUI themes](https://daisyui.com/docs/themes/). Use `data-theme="name"` on `html` or a parent to switch.

## Component Patterns

### Buttons

Base: `btn`. Combine with color, size, style modifiers.

```html
<button class="btn btn-primary">Primary</button>
<button class="btn btn-outline btn-sm">Outline Small</button>
<button class="btn btn-ghost btn-lg">Ghost Large</button>
<button class="btn btn-error btn-block">Full Width Error</button>
```

**Colors**: `btn-neutral`, `btn-primary`, `btn-secondary`, `btn-accent`, `btn-info`, `btn-success`, `btn-warning`, `btn-error`  
**Styles**: `btn-outline`, `btn-soft`, `btn-ghost`, `btn-link`, `btn-active`  
**Sizes**: `btn-xs`, `btn-sm`, `btn-md`, `btn-lg`, `btn-xl`  
**Layout**: `btn-block`, `btn-wide`, `btn-square`, `btn-circle`  
**State**: `btn-disabled` or `disabled` attribute

Loading: `<span class="loading loading-spinner"></span>` inside the button.

### Cards

Structure: `card` > `card-body` > `card-title`, `card-actions`. Optional `figure` for images.

```html
<div class="card bg-base-100 shadow-sm">
  <figure>
    <img src="..." alt="..." />
  </figure>
  <div class="card-body">
    <h2 class="card-title">Title</h2>
    <p>Content...</p>
    <div class="card-actions justify-end">
      <button class="btn btn-primary">Action</button>
    </div>
  </div>
</div>
```

**Modifiers**: `card-border`, `card-dash`, `card-side` (horizontal layout), `card-xs` through `card-xl`  
**Image full**: Add `image-full` to card for overlay image behind body.

### Modals

Use `<dialog>` with `showModal()` or checkbox/anchor for pure HTML.

**JavaScript method** (preferred):

```html
<button class="btn" onclick="my_modal.showModal()">Open</button>
<dialog id="my_modal" class="modal">
  <div class="modal-box">
    <h3 class="font-bold text-lg">Title</h3>
    <p class="py-4">Content</p>
    <div class="modal-action">
      <form method="dialog">
        <button class="btn">Close</button>
      </form>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>
```

**Checkbox method** (no JS):

```html
<label for="my_modal" class="btn">Open</label>
<input type="checkbox" id="my_modal" class="modal-toggle" />
<div class="modal" role="dialog">
  <div class="modal-box">...</div>
  <label for="my_modal" class="modal-backdrop">close</label>
</div>
```

**Position**: `modal-top`, `modal-middle`, `modal-bottom`, `modal-start`, `modal-end`

### Forms and Inputs

```html
<div class="form-control">
  <label class="label">
    <span class="label-text">Email</span>
  </label>
  <input type="email" placeholder="Email" class="input input-bordered" />
  <label class="label"><span class="label-text-alt text-error">Error message</span></label>
</div>
```

**Input**: `input` + `input-bordered` (or `input-ghost`). Sizes: `input-sm`, `input-lg`  
**Textarea**: `textarea textarea-bordered`  
**Checkbox**: `checkbox`, **Toggle**: `toggle`, **Select**: `select select-bordered`  
**Label**: `label`, `label-text`, `label-text-alt`

### Navbar

```html
<div class="navbar bg-base-100 shadow-sm">
  <div class="navbar-start">...</div>
  <div class="navbar-center">...</div>
  <div class="navbar-end">...</div>
</div>
```

Use `flex-1`, `flex-none` for simple layouts. Combine with `dropdown`, `menu`, `input` for search. For responsive: `dropdown` on mobile, `menu menu-horizontal` on desktop with `hidden lg:flex`.

### Alerts

```html
<div role="alert" class="alert alert-info">
  <span>Message</span>
</div>
```

**Colors**: `alert-info`, `alert-success`, `alert-warning`, `alert-error`  
**Styles**: `alert-outline`, `alert-soft`, `alert-dash`  
**Layout**: `alert-vertical` (mobile), `alert-horizontal` (desktop)

### Dropdowns

```html
<div class="dropdown dropdown-end">
  <div tabindex="0" role="button" class="btn">Open</div>
  <ul tabindex="0" class="menu dropdown-content bg-base-100 rounded-box z-[1] mt-3 w-52 p-2 shadow">
    <li><a>Item 1</a></li>
    <li><a>Item 2</a></li>
  </ul>
</div>
```

**Position**: `dropdown-end`, `dropdown-top`, `dropdown-bottom`, `dropdown-left`, `dropdown-right`

### Menus

```html
<ul class="menu bg-base-200 rounded-box w-56">
  <li><a>Item</a></li>
  <li>
    <details>
      <summary>Parent</summary>
      <ul><li><a>Sub 1</a></li></ul>
    </details>
  </li>
</ul>
```

Horizontal: `menu menu-horizontal`

### Badges

`badge` + `badge-primary`, `badge-outline`, `badge-sm`, etc. Use with `badge-info`, `badge-success`, etc.

### Loading

`loading`, `loading-spinner`, `loading-dots`, `loading-ring`

## Semantic Colors

Use theme-aware colors: `bg-primary`, `text-secondary`, `btn-accent`, `text-base-content`, `bg-base-100`, `bg-base-200`, `bg-base-300`. These adapt to themes and dark mode.

## Workflow

1. Choose the component (btn, card, modal, etc.)
2. Add base class + semantic modifiers
3. Use Tailwind for layout (flex, grid, p-4, gap-2) and overrides
4. Prefer daisyUI color modifiers over custom Tailwind colors for consistency

## Additional Resources

- Component reference: [reference.md](reference.md)
- Full docs: https://daisyui.com/docs/
- Components: https://daisyui.com/components/
