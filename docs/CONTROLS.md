# Reusable UI Controls

The FlexiRule Rule Builder is built on a library of sophisticated, reusable Vue 3 controls designed for the Frappe ecosystem. These controls handle complex metadata introspection, dynamic viewport positioning, and advanced data mapping.

## Core Controls

### ValueResolverControl
The primary control for defining values that can be static, dynamic (from `doc` or `vars`), or templated (Jinja).
- **Auto-Flipping**: Detects its position relative to the viewport. If the dropdown or overlay would overflow the bottom of the screen, it automatically flips to open upwards.
- **Intelligent Teleportation**: Uses Vue's `<Teleport to="body">` to escape `overflow: hidden` containers (like graph nodes or side panels) while maintaining correct z-index stacking.
- **Legacy Compatibility**: Gracefully handles schemas from older versions while generating modern Jinja snippets for the backend.
- **Context Awareness**: Introspects available fields based on the selected DocType or the current `vars` scope.

### ResourceMapperControl
Used in Document Actions and Processes to map data between different schemas.
- **Field Matching**: Provides a split-pane UI for mapping source fields (or templates) to target DocType fields.
- **Type Validation**: Highlights potential type mismatches (e.g., trying to map a text field to a numeric field).
- **Batch Mapping**: Supports "Map All" functionality for identical field names.

### ComboBoxControl
An enhanced searchable dropdown that supports both static options and dynamic links.
- **Frappe Link Integration**: Can be configured to fetch options from any Frappe DocType via the standard `frappe.call` API.
- **Custom Rendering**: Supports custom templates for dropdown items (e.g., showing both `item_code` and `item_name`).

### TextGeneratorControl
A specialized editor for building complex strings using a mix of static text and dynamic "pills".
- **Mention-style UI**: Typing `@` or `{{` triggers a field picker for inserting dynamic variables.
- **Live Preview**: Renders a sample of the generated Jinja template in real-time.

### TransformControl
Used for data shape manipulation (e.g., converting a list of records into a summarized dictionary).
- **Visual Mapping**: Uses a graph-like interface to define transformations.
- **Standard Functions**: Includes built-in filters like `unique`, `sum`, `map`, and `filter`.

---

## Technical Patterns

### Teleport & Z-Index Management
To ensure overlays (dropdowns, pickers) always appear above other UI elements, FlexiRule uses a standard "Teleport to Body" pattern:
```vue
<template>
  <div class="control-container">
    <button @click="isOpen = !isOpen">Open</button>
    <Teleport to="body">
      <div v-if="isOpen" class="floating-overlay" :style="positionStyle">
        <!-- Overlay Content -->
      </div>
    </Teleport>
  </div>
</template>
```

### Viewport Detection (Auto-Flip)
Floating controls use a custom `useFloating` composable that monitors the element's `getBoundingClientRect()` to decide the optimal rendering direction (Top vs Bottom).

### Frappe Utility Integration
Controls are deeply integrated with Frappe's utility functions. For example, `ValueResolverControl` can automatically generate Jinja snippets that use `frappe.utils.format_value` or `frappe.db.get_value` based on the user's visual selection.
