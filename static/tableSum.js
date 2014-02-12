var nodeList = document.getElementsByClassName("value");
var valuesArr = [];

for (var i = 0; i < nodeList.length - 2; i++) {
    var mv = parseFloat(nodeList[i].innerHTML.replace(/\s/,'').replace(/,/,''));
    valuesArr.push(mv);
}

var sum = valuesArr.reduce(function (a, b) {
    return a + b;
}, 0)

table = document.getElements