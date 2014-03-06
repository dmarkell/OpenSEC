var margin = {top: 20, right: 10, bottom: 30, left: 50},
    height = 300 - margin.top - margin.bottom,
    width = 585 - margin.left - margin.right;

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
    .ticks(6)
    .tickFormat(d3.time.format('%m/%Y'));

var yAxis = d3.svg.axis()
    .scale(y)
    .orient("left");

var area = d3.svg.area()
    .interpolate("monotone")
    .x(function(d) { return x(dateFn(d)); })
    .y0(height)
    .y1(function(d) { return y(closeFn(d)); });

var svg = d3.select(".chart").append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
  .append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

var data = JSONData.slice();

x.domain(d3.extent(data.map(dateFn)));
y.domain([0, d3.max(data.map(closeFn))]);

svg.append("path")
    .datum(data)
    .attr("class", "area")
    .attr("d", area);

svg.append("g")
    .attr("class", "x axis")
    .attr("transform", "translate(0," + height + ")")
    .call(xAxis);

svg.append("g")
    .attr("class", "y axis")
    .call(yAxis);

