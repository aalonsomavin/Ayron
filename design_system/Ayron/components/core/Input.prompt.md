Single-line text field. Use `leading` for a search/field icon and `trailing` for a unit or keyboard hint. Set `invalid` to surface validation errors.

```jsx
<Input placeholder="Search sources" leading={<SearchIcon/>} />
<Input placeholder="Table name" invalid trailing={<span>required</span>} />
```

Notes:
- Focus shows the 3px blue ring; never remove the focus state.
- Pair with a label above (Geist 13/500) — the component is the field only.
