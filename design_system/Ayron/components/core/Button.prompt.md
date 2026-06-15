Primary action trigger — use solid `primary` (ink) for the single main action on a view; `secondary` for adjacent actions, `ghost` for low-emphasis/toolbar actions, `danger` for destructive, `link` for inline navigation.

```jsx
<Button variant="primary" size="md" onClick={ask}>Ask Ayron</Button>
<Button variant="secondary" leftIcon={<PlusIcon/>}>Connect a source</Button>
<Button variant="ghost" size="sm">Cancel</Button>
```

Notes:
- One `primary` per view. Sentence case labels, lead with a verb.
- Sizes: `sm` (30px) dense tables/toolbars, `md` (36px) default, `lg` (44px) hero/forms.
- `leftIcon`/`rightIcon` accept any 16px icon node; spacing is handled.
