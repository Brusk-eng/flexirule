class MockRule:
	def __init__(self, d):
		self.d = d

	def get(self, k):
		return self.d.get(k)

	def test(self):
		status_to_state = {
			"Draft": "Draft",
			"Active": "Active",
			"Disabled": "Inactive",
			"Archived": "Archived",
		}
		state_to_status = {
			"Draft": "Draft",
			"Active": "Active",
			"Inactive": "Disabled",
			"Archived": "Archived",
		}

		state = self.get("lifecycle_state")
		status = self.get("status")
		active_flag = self.get("is_active")

		if not state and status in status_to_state:
			state = status_to_state.get(status)

		if not state:
			state = "Active" if active_flag in (1, True, "1") else "Draft"
		elif active_flag in (1, True, "1"):
			state = "Active"
		elif active_flag in (0, False, "0") and state == "Active":
			state = "Draft"

		self.d["lifecycle_state"] = state
		self.d["is_active"] = 1 if self.d.get("lifecycle_state") == "Active" else 0

		if status not in ("Error", "Invalid"):
			self.d["status"] = state_to_status.get(self.d["lifecycle_state"], "Draft")


m = MockRule({"status": "Draft", "is_active": 1})
m.test()
print(m.d)
