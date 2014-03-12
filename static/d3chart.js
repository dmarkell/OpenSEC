var aspect = 300 / 585;

var chart = d3.select(".chart");

var margin = {top: 20, right: 10, bottom: 20, left: 25},
    targetWidth = parseInt(chart.style("width"), 10),
    width = targetWidth - margin.left - margin.right, // 585px width
    height = targetWidth * aspect - margin.top - margin.bottom; // 300px height

var x = d3.time.scale()
    .range([0, width]);

var y = d3.scale.linear()
    .range([height, 0]);

var parseDate = d3.time.format("%Y-%m-%d").parse,
    dateFn = function(d) { return parseDate(d.Date) },
    closeFn = function(d) { return +d.AdjClose };

var xAxis = d3.svg.axis()
    .scale(x)
    .orient("bottom")
    .tickFormat(d3.time.format('%m/%Y'));

var yAxis = d3.svg.axis()
    .scale(y)
    .orient("left");

var line = d3.svg.line()
    .x(function(d) { return x(dateFn(d)); })
    .y(function(d) { return y(closeFn(d)); });

var svg = chart.append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
  .append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

var data = JSONData.slice();
var barWidth = width / data.length;

x.domain(d3.extent(data.map(dateFn)));
y.domain([0, d3.max(data.map(closeFn))]);

svg.append("g")
    .attr("class", "x axis")
    .attr("transform", "translate(0," + height + ")")
    .call(xAxis);

svg.append("g")
    .attr("class", "y axis")
    .call(yAxis);

svg.append("path")
    .datum(data)
    .attr("class", "line")
    .attr("d", line);

var hoverLineGroup = svg.append("g")
    .attr("class", "hover-line");

var hoverLine = hoverLineGroup
    .append("line")
      .attr("x1", margin.left).attr("x2", margin.left)
      .attr("y1", 0).attr("y2", height)
      .style("opacity", 1e-6);

chart.on("mouseover", function() {
}).on("mousemove", function() {
    var mouse_x = d3.mouse(this)[0];
    if (mouse_x > margin.left && mouse_x < margin.left + width) {
        var mouse_y = d3.mouse(this)[0];
        hoverLine
            .attr("x1", mouse_x - margin.left)
            .attr("x2", mouse_x - margin.left)
            .style("opacity", 0.5)
    } else {
        hoverLine.style("opacity", 1e-6);
    };
}).on("mouseout", function() {
    hoverLine.style("opacity", 1e-6);
});
    
d3.select(window).on("resize", resize);

function resize() {
    // update width
    targetWidth = parseInt(chart.style("width"), 10) - margin.left - margin.right;
    width = width - margin.left - margin.right;
    height = aspect * targetWidth - margin.top - margin.bottom;
}
