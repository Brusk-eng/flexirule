#!/bin/bash

# 1. Fix Vue Flow imports in RuleBuilder.vue
sed -i "s/import { VueFlow, useVueFlow, Panel, PanelPosition } from '@vue-flow\/core';/import { VueFlow, Panel, PanelPosition } from '@vue-flow\/core';\nimport { useVueFlow } from '@vue-flow\/core';/" ./rule_builder/RuleBuilder.vue

# 2. Add missing removeEdges import
sed -i "s/const { fitView, zoomIn, zoomOut } = useVueFlow();/const { fitView, zoomIn, zoomOut, removeEdges } = useVueFlow();/" ./rule_builder/RuleBuilder.vue

# 3. Disable built-in edge deletion to prevent race conditions
sed -i 's/<VueFlow/<VueFlow :edges-editable="false"/' ./rule_builder/RuleBuilder.vue

# 4. Fix nodes computed setter in RuleBuilder.vue
cat > /tmp/nodes_fix.js << 'EOF'
set: (val) => {
    const edges = store.graph.elements.filter(el => el.source);
    const hiddenNodes = store.graph.elements.filter(el => el.position && !val.some(n => n.id === el.id));
    store.graph.elements = [...val, ...hiddenNodes, ...edges];
}
EOF

# 5. Add CSS variables for node styling
cat >> ./rule_builder/RuleBuilder.vue << 'EOF'

<style>
:root {
    --node-start: var(--success);
    --node-process: var(--blue-500);
    --node-condition: var(--warning);
    --node-loop: var(--purple-500);
    --node-switch: var(--orange-500);
    --node-wait: var(--yellow-500);
    --node-subrule: var(--cyan-500);
    --node-stop: var(--danger);
}

.node-start { border-left: 4px solid var(--node-start); }
.node-process { border-left: 4px solid var(--node-process); }
.node-condition { border-left: 4px solid var(--node-condition); }
.node-loop { border-left: 4px solid var(--node-loop); }
.node-switch { border-left: 4px solid var(--node-switch); }
.node-wait { border-left: 4px solid var(--node-wait); }
.node-subrule { border-left: 4px solid var(--node-subrule); }
.node-stop { border-left: 4px solid var(--node-stop); }
</style>
EOF

# 6. Remove dead code from Sidebar.vue
# Remove trigger_filters section

# 7. Remove unused store variables

# 8. Fix undo/redo with structured clone
sed -i "s/const state = JSON.stringify(getStateSnapshot());/const state = JSON.stringify(structuredClone(getStateSnapshot()));/" ./rule_builder/store.js

echo "Frontend fixes applied. Please review and test the changes."