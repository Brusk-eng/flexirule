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
	return JSON.stringify({
		mode,
		referenceDoctype,
		referenceDocname,
		doctypeName: config.doctype_name,
		reportName: config.report_name,
		fields: config.fields,
		resultShape: config.result_shape,
		fetchStrategy: config.fetch_strategy,
		field: config.field,
		aggField: config.agg_field,
		groupBy: config.group_by,
		groupByField: config.group_by_field,
	});
}
