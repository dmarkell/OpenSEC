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
    closeFn = function(d) { return +d.AdjClose },
    formatCurrency = d3.format("$,.2"),
    next_i = function(data, lookup) {
        var right_arr = data.filter(function(d) {
            return dateFn(d) >= lookup
        });
        return data.length - right_arr.length;
    };

var xAxis = d3.svg.axis()
    .scale(x)
    .orient("bottom")
    .tickFormat(d3.time.format('%b %Y'));

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
    .attr("class", "plot")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

var data = JSONData.slice(0, 252*5);
data.sort(function(a, b) {
      return dateFn(a) - dateFn(b);
    });

x.domain(d3.extent(data.map(dateFn)));
y.domain([0, d3.max(data.map(closeFn))]);

svg.append("g")
    .attr("class", "x axis")
    .attr("transform", "translate(0," + height + ")")
    .call(xAxis.ticks(d3.time.months, 6));

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

focus.append("text")
    .attr("x", -30)
    .attr("y", -20)
    .attr("dy", ".35em");

var hoverLine1 = hoverLineGroup
    .append("line")
      .attr("x1", margin.left).attr("x2", margin.left)
      .attr("y1", 0).attr("y2", height)
      .style("opacity", 1e-6);

var hoverLine2 = hoverLineGroup
    .append("line")
      .attr("x1", 0).attr("x2", width)
      .attr("y1", 0).attr("y2", 0)
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
        hoverLine1
            .attr("x1", mouse_x - margin.left)
            .attr("x2", mouse_x - margin.left)
            .style("opacity", 0.3);
        hoverLine2
            .attr("y1", y(closeFn(d)))
            .attr("y2", y(closeFn(d)))
            .style("opacity", 0.3);
        focus
            .style("display", null)
            .attr("transform", "translate(" + x(dateFn(d)) + "," + y(closeFn(d)) + ")")
            .select("text").text(formatCurrency(closeFn(d)));

    } else {
        hoverLine1.style("opacity", 1e-6);
        hoverLine2.style("opacity", 1e-6);
        focus.style("display", "none");
    };
}).on("mouseout", function() {
    hoverLine1.style("opacity", 1e-6);
    hoverLine2.style("opacity", 1e-6);
});
    
d3.select(window).on("resize", resize);

function resize() {
    // update width
    targetWidth = parseInt(chart.style("width"), 10);
    width = targetWidth - margin.left - margin.right;
    height = aspect * targetWidth - margin.top - margin.bottom;
    console.log(targetWidth, width, height);

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
        .call(xAxis.ticks(d3.time.months, 6));

    d3.selectAll(".y")
        .attr("class", "y axis")
        .call(yAxis);

    d3.selectAll(".line")
        .datum(data)        
        .attr("d", line);

    hoverLine1.attr("y1", 0).attr("y2", height)
    hoverLine2.attr("x1", 0).attr("x2", width)

}
