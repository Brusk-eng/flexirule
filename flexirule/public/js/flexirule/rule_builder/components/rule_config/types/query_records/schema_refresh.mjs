/**
 * Return a stable signature for inputs that determine Query Records output schema.
 *
 * Filters, sorting, and limits intentionally do not participate: they change
 * which rows are returned, not the set or types of output fields.
 */
export function getQueryRecordsSchemaRefreshSignature({
	mode,
	referenceDoctype,
	referenceDocname,
	config = {},
} = {}) {
	const isQueryDoc = mode === "Query Doc";
	const isQueryReport = mode === "Query Report";
	const usesSelectedFields = ["Fetch Records", "Query List", "Query Doc"].includes(mode);
	const usesAggregation = ["Sum", "Average", "Min", "Max"].includes(mode);
	const usesAggregateField = usesAggregation || mode === "Group By";
	return JSON.stringify({
		mode,
		referenceDoctype,
		referenceDocname: isQueryReport ? referenceDocname : null,
		doctypeName: isQueryDoc ? config.doctype_name : null,
		reportName: isQueryReport ? config.report_name : null,
		fields: usesSelectedFields ? config.fields : null,
		resultShape: mode === "Fetch Records" ? config.result_shape : null,
		fetchStrategy: isQueryDoc ? config.fetch_strategy : null,
		field: usesAggregation ? config.field : null,
		aggField: usesAggregateField ? config.agg_field : null,
		aggFunction: mode === "Group By" ? config.agg_function : null,
		groupBy: ["Query List", "Fetch Records"].includes(mode) ? config.group_by : null,
		groupByField: mode === "Group By" ? config.group_by_field : null,
	});
}
