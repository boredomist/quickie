"use strict";

// String truncate
String.prototype.truncate = function(n){
    return this.substr(0,n-1)+(this.length > n ? '...' : '');
};

var Quickie = {};

Quickie.data = null;
Quickie.series = [];

Quickie.initialize = function(data) {
    Quickie.data = data;

    Quickie.prepareData();
    Quickie.initInfo();
    Quickie.initPlot();
}

Quickie.initPlot = function() {
    var options =  {
        series: {
            lines: { show: true },
            points: { show: true }
        },

        grid: {
            hoverable: true,
            clickable: true
        },

        xaxis: {
            mode: "time",
            timezone: "broswer",
            min: this.data.first_run
        },

        yaxis: {
            min: 0,
            tickFormatter: function(num, obj) {
                return num.toFixed(3) + " s";
            }
        },

        legend: {
            show: true,
            position: "ne"
        }
    };

    $('#plot-container').resizable({
        minWidth: 400,
        minHeight: 550
    });

    this.plot = $.plot('#placeholder', Quickie.series, options);

    this.overview = $.plot('#overview', Quickie.series, {
	series: {
            lines: {
                show: true,
                lineWidth: 1
            },
            shadowSize: 0
        },
        legend: {
            show: false
        },
        xaxis: {
            ticks: [],
            mode: "time"
        },
        yaxis: {
            ticks: [],
            min: 0,
            autoscaleMargin: 0.1
        },
        selection: {
            mode: "x"
        }
    });

    var previous = null;
    $('#placeholder').bind('plothover', function(event, pos, item) {
        if(item && previous != item.dataIndex) {
            previous = item.dataIndex;

            $("#tooltip").remove();

            var command = item.series.cmd;
            var series = Quickie.data.run_data[command];
            var run = series[item.dataIndex];
            var lastRun = series[item.dataIndex == 0 ? 0 :
                                 item.dataIndex - 1];

            // Make note of the change since the last run
            var delta = run[1] - lastRun[1];
            var percent = (run[1] - lastRun[1]) / lastRun[1] * 100;

            delta = delta.toFixed(3);
            percent = percent.toFixed(1);

            if(delta > 0) {
                delta = "+" + delta;
                percent = "+" + percent;
            }

            var repo_info = "";

            // Is it empty?
            if(run[2].toSource() !== "({})") {
                repo_info = Mustache.render("{{commit}}@{{branch}}",
                                            { commit: run[2].commit,
                                              branch: run[2].branch});
            } else {
                repo_info = "No git data";
            }

            var html = Mustache.render(
                "<b>Git:</b> {{repo_info}}<br>" +
                    "<b>Time:</b> {{time}} seconds <br>" +
                    "<b>Δs:</b> {{delta}} s, {{percent}}%<br>" +
                    "<b>Command:</b> {{command}}<br>" +
                    "<b>Built at:</b> {{date}}<br>",

                {
                    delta: delta,
                    percent: percent,
                    repo_info: repo_info,
                    command: command,
                    date: new Date(run[0] * 1000).toLocaleString(),
                    time: run[1].toFixed(3),
                    commit: run[2]
                });

            $("<div id='tooltip'>" + html + "</div>").css({
                position: 'absolute',
                display: 'none',
                top: item.pageY + 5,
                left: item.pageX + 5,
                border: '1px solid #fdd',
                padding: '2px',
                'background-color': '#fee',
                opacity: 0.80
            }).appendTo('body').fadeIn(200);
        } else if(item == null) {
            $('#tooltip').fadeOut(500);
            previous = null;
        }
    });


    $('#placeholder').bind('plotselected', function(event, ranges) {
        Quickie.plot = $.plot('#placeholder', Quickie.series,
                              $.extend(true, {}, options, {
	                          xaxis: {
                                      min: ranges.xaxis.from,
                                      max: ranges.xaxis.to
                                  }
                              }));

        Quickie.overview.setSelection(ranges, true);
    });

    $("#overview").bind("plotselected", function (event, ranges) {
        Quickie.plot.setSelection(ranges);
    });


}

Quickie.initInfo = function() {
    var info = $('#info');
    var template = info.html();

    document.title = this.data.repository + ' :: Quickie';

    var replacements = {
        reponame: this.data.repository,
        firstrun: new Date(this.data.first_run).toLocaleString(),
        lastrun: new Date(this.data.last_run).toLocaleString()
    };

    info.html(Mustache.render(info.html(), replacements));

    // TODO: fill this out some.
}


Quickie.prepareData = function() {
    var i = 0;

    // Push all the data
    $.each(Quickie.data.run_data, function(name, runs) {
        // Convert unix timestamp to milliseconds
        var runData = $.map(runs, function(e) {
            return [[e[0] * 1000, e[1], e[2]]];
        });

        Quickie.series.push({
            cmd: name,
            color: i++,
            label: name.truncate(50),
            data: runData
        });
    });

    // Convert seconds to milliseconds
    this.data.first_run *= 1000;
    this.data.last_run *= 1000;
}
