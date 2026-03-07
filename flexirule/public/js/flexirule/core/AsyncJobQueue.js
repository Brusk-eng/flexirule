/**
 * flexirule/core/AsyncJobQueue.js
 * Serializes async tasks per key.
 */

export default class AsyncJobQueue {
	constructor() {
		this.queues = {}; // key -> Promise
	}

	/**
	 * Run a task in the queue for a specific key.
	 * @param {string} key - Unique key for the queue (e.g. 'fieldname' or 'row:fieldname')
	 * @param {Function} task - Async function to execute
	 */
	run(key, task) {
		if (!this.queues[key]) {
			this.queues[key] = Promise.resolve();
		}

		this.queues[key] = this.queues[key].then(async () => {
			try {
				await task();
			} catch (e) {
				console.error(`AsyncJobQueue: Task failed for key "${key}":`, e);
			}
		});

		return this.queues[key];
	}

	/**
	 * Wait for all tasks in a specific queue to complete.
	 */
	async wait(key) {
		if (this.queues[key]) {
			await this.queues[key];
		}
	}

	/**
	 * Wait for ALL queues to complete.
	 */
	async waitAll() {
		await Promise.all(Object.values(this.queues));
	}
}

frappe.provide("flexirule.core");
flexirule.core.AsyncJobQueue = AsyncJobQueue;
