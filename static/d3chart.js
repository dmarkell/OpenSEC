
var chart = d3.select(".chart");

var parseDate = d3.time.format("%Y-%m-%d").parse,
    dateFn = function(d) { return parseDate(d.Date) },
    closeFn = function(d) { return +d.AdjClose },
    formatCurrency = d3.format("$,.2f"),
    formatDate = d3.time.format('%b %d, %Y')
    next_i = function(data, lookup) {
        var right_arr = data.filter(function(d) {
            return dateFn(d) >= lookup
        });
        return data.length - right_arr.length;
    };

var data = JSONData.slice(0, 252*5);
data.sort(function(a, b) {
      return dateFn(a) - dateFn(b);
    });
var last = data[data.length - 1];
var fattest = d3.max(data.map(function(d) {return formatCurrency(closeFn(d)).length ;}))

var margin = {top: 20, right: 10, bottom: 20, left: fattest * 7},
    aspect = 300 / 585,
    targetWidth = parseInt(chart.style("width"), 10),
    width = targetWidth - margin.left - margin.right, // 585px width
    height = targetWidth * aspect - margin.top - margin.bottom; // 300px height

var x = d3.time.scale()
    .range([0, width])
    .domain(d3.extent(data.map(dateFn)));

var y = d3.scale.linear()
    .range([height, 0])
    .domain([0, d3.max(data.map(closeFn))]);

var xAxis = d3.svg.axis()
    .scale(x)
    .orient("bottom")
    .tickFormat(d3.time.format('%b %Y'));

var yAxis = d3.svg.axis()
    .scale(y)
    .orient("left")
    .tickFormat(formatCurrency);

var line = d3.svg.line()
    .x(function(d) { return x(dateFn(d)); })
    .y(function(d) { return y(closeFn(d)); });

var svg = chart.append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
  .append("g")
    .attr("class", "plot")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

svg.append("g")
    .attr("class", "x axis")
    .attr("transform", "translate(0," + height + ")")
    .call(xAxis.ticks(d3.time.months, 12))
  .append("text")
    .attr("class", "last")
    .attr("x", width)
    .attr("y", -10)
    .style("text-anchor", "end")
    .text(formatDate(dateFn(last)) + ": " + formatCurrency(closeFn(last)));

svg.append("g")
    .attr("class", "y axis")
    .call(yAxis);

svg.append("path")
    .datum(data)
    .attr("class", "line")
    .attr("d", line);

var hoverLineGroup = svg.append("g")
    .attr("class", "hover-line");

var focus = svg.append("g")
    .attr("class", "focus")
    .style("display", "none");

focus.append("circle")
    .attr("r", 4.5);

var hoverLineVert = hoverLineGroup
    .append("line")
      .attr("x1", margin.left)
      .attr("x2", margin.left)
      .attr("y1", 0)
      .attr("y2", height)
      .style("opacity", 1e-6);

var hoverLineHoriz = hoverLineGroup
    .append("line")
      .attr("x1", 0)
      .attr("x2", width)
      .attr("y1", 0)
      .attr("y2", 0)
      .style("opacity", 1e-6);

chart.on("mouseover", function() {
}).on("mousemove", function() {
    var mouse_x = d3.mouse(this)[0],
        x0 = x.invert(mouse_x - margin.left),
        i = next_i(data, x0),
        d0 = data[i - 1],
        d1 = data[i];

    if (mouse_x > margin.left && mouse_x < margin.left + width) {
        
        var d = x0 - dateFn(d0) > dateFn(d1) - x0 ? d1 : d0;
        hoverLineVert
            .attr("x1", mouse_x - margin.left)
            .attr("x2", mouse_x - margin.left)
            .style("opacity", 0.3);
        hoverLineHoriz
            .attr("y1", y(closeFn(d)))
            .attr("y2", y(closeFn(d)))
            .style("opacity", 0.3);
        focus
            .style("display", null)
            .attr("transform", "translate(" + x(dateFn(d)) + "," + y(closeFn(d)) + ")")
        d3.select(".last")
            .text(formatDate(dateFn(d)) + ": " + formatCurrency(closeFn(d)));
    } else {
        hoverLineVert.style("opacity", 1e-6);
        hoverLineHoriz.style("opacity", 1e-6);
        focus.style("display", "none");
    };
});
    
d3.select(window).on("resize", resize);

function resize() {
    // update width
    targetWidth = parseInt(chart.style("width"), 10);
    width = targetWidth - margin.left - margin.right;
    height = aspect * targetWidth - margin.top - margin.bottom;

    // update x and y scales
    x.range([0, width]);
    y.range([height, 0]);

    // update stuff that uses width, height, x or y
    d3.selectAll("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom);
    d3.selectAll(".plot")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")")

    d3.selectAll(".x")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis.ticks(d3.time.months, 12));

    d3.select(".last")
        .attr("x", width)
        .text(formatDate(dateFn(last)) + ": " + formatCurrency(closeFn(last)));

    d3.selectAll(".y")
        .attr("class", "y axis")
        .call(yAxis);

    d3.selectAll(".line")
        .datum(data)        
        .attr("d", line);

    hoverLineVert.attr("y1", 0).attr("y2", height)
    hoverLineHoriz.attr("x1", 0).attr("x2", width)

}
