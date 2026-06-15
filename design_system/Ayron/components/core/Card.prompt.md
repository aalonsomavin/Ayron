Content surface. Default is border-only (flat); set `elevated` for a resting shadow or `interactive` for clickable hover lift.

```jsx
<Card title="Revenue" subtitle="Last 30 days" actions={<Button size="sm" variant="ghost">Export</Button>}>
  <Chart/>
</Card>
```

Notes: prefer border-only on dense dashboards; reserve shadows for floating/clickable cards.
