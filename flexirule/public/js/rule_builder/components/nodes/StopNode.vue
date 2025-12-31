<script setup>
import { Handle, Position } from '@vue-flow/core';
import { useStore } from '../../store';

const props = defineProps(['data', 'label', 'id']);
const store = useStore();

function deleteNode() {
    frappe.confirm(
        __('Delete this node?'),
        () => {
            store.delete_node(props.id);
        }
    );
}
</script>

<template>
    <div class="stop-octagon">
        <Handle type="target" :position="Position.Left" class="handle-target"/>
        
        <div class="octagon-content">
            <div class="inner-border">
                <i class="fa fa-hand-paper-o"></i>
                <span class="stop-text">STOP</span>
            </div>
        </div>

        <button class="delete-btn" @click.stop="deleteNode" :title="__('Delete Node')">
            <i class="fa fa-trash"></i>
        </button>
    </div>
</template>

<style scoped>
.stop-octagon {
    width: 100px;
    height: 100px;
    background: var(--danger);
    clip-path: polygon(30% 0%, 70% 0%, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0% 70%, 0% 30%);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    transition: all 0.3s ease;
    filter: drop-shadow(0 4px 8px rgba(220, 53, 69, 0.4));
}

.stop-octagon:hover {
    transform: scale(1.05);
    filter: drop-shadow(0 8px 16px rgba(220, 53, 69, 0.6));
}

.octagon-content {
    color: white;
    z-index: 2;
}

.inner-border {
    width: 80px;
    height: 80px;
    border: 2px solid rgba(255, 255, 255, 0.8);
    clip-path: polygon(30% 0%, 70% 0%, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0% 70%, 0% 30%);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
}

.inner-border i { font-size: 20px; }
.stop-text { font-size: 14px; font-weight: 900; letter-spacing: 1px; }

.delete-btn {
    position: absolute; top: 5px; right: 5px;
    background: white; color: var(--danger); border: none;
    width: 20px; height: 20px; border-radius: 50%;
    display: none; align-items: center; justify-content: center;
    cursor: pointer; z-index: 10;
}
.stop-octagon:hover .delete-btn { display: flex; }

.handle-target {
    background: white !important;
    border: 3px solid var(--danger) !important;
    width: 12px !important; height: 12px !important;
    left: 0px !important;
}
</style>
