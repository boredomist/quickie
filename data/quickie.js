"use strict";

var Quickie = {};

Quickie.data = null;
Quickie.data_points = [];

Quickie.initialize = function(data) {
    Quickie.data = data;

    Quickie.initInfo();
    Quickie.initPlot();
}

Quickie.initPlot = function() {
    this.plot = $('#placeholder').plot([[[1, 2], [10, 20]], [[20,10], [2,1]]], {
        series: {
            lines: { show: true },
            points: { show: true }
        },

        xaxis: {
            show: true,
            position: "bottom",
            timeformat: "%Y/%m/%d"
        },

        legend: {
            show: true,
            position: "ne"
        }

    });
}

Quickie.initInfo = function() {
    var info = $('#info');
    var template = info.html();

    var replacements = {
        reponame: this.data.repository,
        firstrun: this.data.first_run,
        lastrun: this.data.last_run
    };

    info.html(Mustache.render(info.html(), replacements));

    // TODO: this.
}
