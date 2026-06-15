Section switcher with an underline indicator (active tab marked in ink). Add `count` chips for tabs that carry a quantity.

```jsx
<Tabs
  defaultValue="sources"
  onChange={setTab}
  items={[
    { value: "sources", label: "Sources", count: 6 },
    { value: "auto", label: "Automations", count: 3 },
    { value: "activity", label: "Activity" },
  ]}
/>
```
