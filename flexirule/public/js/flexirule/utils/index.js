export function validate_connection(params) {
	// Add validation logic here (e.g., prevent cycles, type mismatch)
	return null;
}

export function generateShortId() {
	// Generate a short, readable ID like "ACT-X9Y2"
	const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
	let result = "";
	for (let i = 0; i < 4; i++) {
		result += chars.charAt(Math.floor(Math.random() * chars.length));
	}
	return `ACT-${result}`;
}
