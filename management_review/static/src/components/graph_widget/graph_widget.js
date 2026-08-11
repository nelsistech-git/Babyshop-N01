/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onMounted, onPatched, onWillUnmount, useRef } from "@odoo/owl";

export class GraphWidget extends Component {
    static template = "management_review.GraphWidget";
    static displayName = _t("Graph Widget");
    static props = {
        ...standardFieldProps,
        graph_type: { type: String, optional: true, default: "line" },
        xlabel: { type: String, optional: true },
        ylabel: { type: String, optional: true },
        update: { type: Function, optional: true },
        value: { type: String, optional: true },
        decorations: { type: Object, optional: true },
        readonly: { type: Boolean, optional: true },
        id: { type: String, optional: true },
        name: { type: String, optional: true },
        type: { type: String, optional: true },
        setDirty: { type: Function, optional: true },
    };

    setup() {
        this.chart = null;
        this.canvasRef = useRef("canvas");

        onMounted(() => this.renderChart());
        onPatched(() => this.renderChart());
        onWillUnmount(() => this.destroyChart());
    }

    destroyChart() {
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
    }

    parseChartData() {
        const rawData = this.props.record?.data?.company_statistics;
        if (!rawData) {
            return [];
        }
        try {
            const parsedData = JSON.parse(rawData);
            return Array.isArray(parsedData) ? parsedData : [];
        } catch {
            return [];
        }
    }

    renderChart() {
        const canvasElement = this.canvasRef.el;
        if (!canvasElement || typeof Chart === "undefined") {
            return;
        }

        const parsedData = this.parseChartData();
        const config = this.getLineChartConfig(parsedData);
        this.destroyChart();

        if (!config) {
            return;
        }

        const context = canvasElement.getContext("2d");
        if (!context) {
            return;
        }

        this.chart = new Chart(context, config);
    }

    getLineChartConfig(parsedData) {
        if (!parsedData.length || !parsedData[0]?.values?.length) {
            return null;
        }

        const labels = parsedData[0].values.map((point) => point.x);
        const datasets = parsedData.map((dataset) => {
            const strokeColor = dataset.color || "#1f6f78";
            return {
                data: (dataset.values || []).map((point) => point.y),
                label: dataset.key,
                borderColor: strokeColor,
                backgroundColor: dataset.area ? `${strokeColor}33` : "transparent",
                borderWidth: 2,
                fill: Boolean(dataset.area),
                tension: 0.25,
            };
        });

        return {
            type: this.props.graph_type || "line",
            data: {
                labels,
                datasets,
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                legend: { display: true },
                scales: {
                    yAxes: [{
                        display: true,
                        scaleLabel: {
                            display: true,
                            labelString: this.props.ylabel || "Value in BDT",
                            fontSize: 14,
                        },
                        ticks: {
                            beginAtZero: true,
                        },
                    }],
                    xAxes: [{
                        display: true,
                        scaleLabel: {
                            display: true,
                            labelString: this.props.xlabel || "Last Three Month (Day)",
                            fontSize: 14,
                        },
                    }],
                },
                elements: {
                    line: {
                        backgroundColor: "transparent",
                    },
                },
                tooltips: {
                    intersect: false,
                    position: "nearest",
                    caretSize: 0,
                },
            },
        };
    }
}

export const graphWidget = {
    component: GraphWidget,
    supportedTypes: ["float", "integer", "monetary"],
};

registry.category("fields").add("graph_widget", graphWidget);
