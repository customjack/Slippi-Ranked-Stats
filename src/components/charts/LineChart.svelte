<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import * as echarts from "echarts";

  interface Marker {
    x: string;
    y: number;
    name: string;
  }

  let {
    xData,
    yData,
    label = "",
    color = "#2ecc71",
    fill = false,
    markers = [] as Marker[],
    height = 240,
  }: {
    xData: (string | number)[];
    yData: number[];
    label?: string;
    color?: string;
    fill?: boolean;
    markers?: Marker[];
    height?: number;
  } = $props();

  let container: HTMLDivElement;
  let chart: echarts.ECharts | null = null;

  function buildOption() {
    return {
      backgroundColor: "transparent",
      textStyle: { color: "#888" },
      grid: { left: 50, right: 20, top: 20, bottom: 40 },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#2b2b2b",
        borderColor: "#3a3a3a",
        textStyle: { color: "#e0e0e0" },
      },
      xAxis: {
        type: "category",
        data: xData,
        axisLine: { lineStyle: { color: "#3a3a3a" } },
        axisLabel: { color: "#666", fontSize: 11 },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        axisLine: { lineStyle: { color: "#3a3a3a" } },
        axisLabel: { color: "#666", fontSize: 11 },
        splitLine: { lineStyle: { color: "#2a2a2a" } },
      },
      series: [
        {
          name: label,
          type: "line",
          data: yData,
          smooth: true,
          lineStyle: { color, width: 2 },
          itemStyle: { color },
          areaStyle: fill ? { color: color + "22" } : undefined,
          showSymbol: false,
        },
        ...(markers.length > 0
          ? [
              {
                name: "Season End",
                type: "scatter",
                data: markers.map((m) => ({
                  name: m.name,
                  value: [m.x, m.y],
                })),
                symbol: "diamond",
                symbolSize: 10,
                itemStyle: { color: "#f39c12" },
                tooltip: {
                  formatter: (params: any) =>
                    `${params.data.name}: ${params.data.value[1].toFixed(1)}`,
                },
              },
            ]
          : []),
      ],
    };
  }

  onMount(() => {
    chart = echarts.init(container, "dark");
    chart.setOption(buildOption());
    const ro = new ResizeObserver(() => chart?.resize());
    ro.observe(container);
    return () => ro.disconnect();
  });

  $effect(() => {
    chart?.setOption(buildOption(), { notMerge: true });
  });

  onDestroy(() => chart?.dispose());
</script>

<div bind:this={container} style="width:100%; height:{height}px"></div>
