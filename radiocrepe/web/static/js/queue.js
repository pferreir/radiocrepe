$(function() {
    var song_template = Handlebars.compile($("#song_template").html());
    var song_result = Handlebars.compile($("#song_result").html());
    var song_template_now = Handlebars.compile($("#song_template_now").html());
    var prev_result = {time: 0};

    var Item = Backbone.Model.extend({
    });

    var Queue = Backbone.Collection.extend({
        model: Item,
        url: "/queue/"
    });

    var ItemView = Backbone.View.extend({
        tagName: 'li',
        initialize: function() {
            _.bindAll(this, 'render', 'remove', 'update', 'vote_up',
                     'vote_undo');
            this.model.bind('remove', this.remove);
            this.model.bind('change', this.update);
        },
        render: function() {
            var data = this.model.toJSON();
            data.img_path = url_img;
            data.logged_user = logged_user;
            $(this.el).html(song_template(data))
            return this;
        },
        remove: function() {
            $(this.el).fadeOut(function() {
                $(this).remove();
            });
        },
        events: {
            "click div.up_arrow:not(.active)": "vote_up",
            "click div.up_arrow.active": "vote_undo"
        },
        update: function() {
            this.render();
        },
        vote_up: function() {
            var self = this;
            var $arrow = $('div.up_arrow', this.el);
            $.ajax({url: '/queue/' + this.model.get('uid') + '_' +
                    this.model.get('ts_add') + '/vote_up/',
                    type: 'POST',
                    success: function(result) {
                        $arrow.addClass('active');
                        self.model.set('self_vote', true);
                    }});
        },
        vote_undo: function() {
            var self = this;
            var $arrow = $('div.up_arrow', this.el);
            $.ajax({url: '/queue/' + this.model.get('uid') + '_' +
                    this.model.get('ts_add') + '/vote_undo/',
                    type: 'POST',
                    success: function(result) {
                        $arrow.removeClass('active');
                        self.model.set('self_vote', false);
                    }});
        }

    });

    var QueueView = Backbone.View.extend({
        el: $('ul#song_list'),
        initialize: function() {
            this.counter = 0;
            _(this).bindAll('addItem', 'render', 'removeItem');
            this.collection.bind('refresh', this.render);
            this.collection.bind('add', this.addItem);
            this.collection.bind('remove', this.removeItem);
            this.collection.fetch({add: true});
       },
        addItem: function(item) {
            this.counter++;
            var itemView = new ItemView({
                model: item
            });
            $(this.el).append($(itemView.render().el).fadeIn(0));
        },
        removeItem: function(item) {
            item.trigger('remove');
        },
        render: function() {
            _(this.collection.models).each(function(item){
                this.addItem(item);
            }, this);
        }
    });

    var collection = new Queue();

    var view = new QueueView({
        collection: collection
    });

    function update_artist_info(artist) {
        if (artist) {
            $.ajax({url: '/artist/' + encodeURI(artist) + '/',
                   success: function(result) {
                       $('#picture').hide();
                       if (result.artist) {
                           $('#picture').attr('src', result.artist.image[2]['#text']).fadeIn();
                       }
                   }});
        }
    }

    var App = {
        initialize: function() {
            var ws = new WebSocket(url.replace('http', 'ws') + "updates/");

            App.get_current_status()

            $('#play').click(function() {
                App.search($('#term').val());
            });

            $('#term').keypress(function(e){
                if(e.which == 13){
                    App.search($('#term').val());
                }
            });

            ws.onopen = function() {
                console.debug('websocket connection established');
            };

            ws.onmessage = function(msg) {
                result = JSON.parse(msg.data);
                console.debug('got', result)
                if (result) {
                    if (result.mtype == 'add') {
                        App.add(result.data, result.ts);
                    } else if (result.mtype == 'play') {
                        App.play(result.data.song, result.ts, result.data.user);
                    } else if (result.mtype == 'stop') {
                        App.stop();
                    } else if (result.mtype == 'attach') {
                        NotificationMgr.create(result.data.node_id, 'storage attached');
                    } else if (result.mtype == 'detach') {
                        NotificationMgr.create(result.data.node_id, 'storage detached');
                    } else if (result.mtype == 'login') {
                        NotificationMgr.create('', result.data, 'login')
                    } else if (result.mtype == 'vote_up') {
                        App.vote_up(result.data);
                    }  else if (result.mtype == 'vote_undo') {
                        App.vote_undo(result.data);
                    }

                }
            };
        },
        get_current_status: function() {
            $.ajax({url: '/playing/',
                    type: 'GET',
                    success: function(result) {
                        if (result) {
                            App.play(result, result.time_add);
                        } else {
                            App.stop();
                        }
                    }});
        },
        play: function (song, time_add, added_by) {
            if (added_by !== undefined) {
                song.added_by = added_by;
            }
            $("#now").html(song_template_now(song))
            _(collection.models).each(function(item){
                if (item.get('ts_add') <= time_add) {
                    collection.remove(item);
                }
            });
            update_artist_info(song.artist);
            console.debug('playing', song);
        },

        stop: function() {
            $("#now").text("Nothing")
            $("#picture").hide();
        },

        add: function(data, time_add) {
            NotificationMgr.create(
                data.song.artist + ' - ' + data.song.title,
                data.user, 'enqueue');
            data.song.ts_add = time_add;
            data.song.added_by = data.user;
            data.song.num_votes = data.num_votes;
            data.song.self_vote = data.self_vote;
            console.debug('adding', data.song);
            collection.add(data.song);
        },

        vote_up: function(data) {
            var res = collection.where({
                uid: data.uid,
                ts_add: data.ts_add
            });

            if (res) {
                res[0].set('num_votes', res[0].get('num_votes') + 1);
            } else {
                console.error('no such song found', data);
            }
        },

        vote_undo: function(data) {
            var res = collection.where({
                uid: data.uid,
                ts_add: data.ts_add
            });

            if (res) {
                res[0].set('num_votes', res[0].get('num_votes') - 1);
            } else {
                console.error('no such song found', data);
            }
        },

        search: function(term) {
            $.ajax({url: '/play/' + encodeURI(term) + '/',
                    dataType: 'json',
                    type: 'POST',
                    success: function(result) {
                        $('#term').val('').focus();
                        if ($.isArray(result)) {
                            App.show_chooser(result);
                        }
                    },
                    error: function() {
                        alert('Sorry, nothing found');
                        $('#term').focus()
                    }});
        },

        show_chooser: function(songs) {
            $('#term').qtip({
                content: {
                    text: function() {
                        var tip = this;
                        var list = $('<ul id="result_list"></ul>')
                        _.each(songs, function(song) {
                            list.append(song_result(song));
                        });
                        list.on('click', 'a', function() {
                            App.enqueue($(this).data('uid'));
                            tip.qtip('destroy');
                            return false;
                        });
                        return list;
                    },
                    title: {
                        text: 'Search results',
                        button: true
                    }
                },
                position: {
                    my: 'center',
                    at: 'center',
                    target: $(window)
                },
                show: {
                    event: null,
                    solo: true,
                    modal: true,
                    ready: true
                },
                style: {
                    width: '400px',
                    classes: 'ui-tooltip-light ui-tooltip-rounded'
                }
            });

        },

        enqueue: function(uid) {
            $.ajax({url: '/enqueue/' + encodeURI(uid) + '/',
                    dataType: 'json',
                    type: 'POST',
                    success: function(result) {
                    },
                    error: function() {
                        alert('Something wrong while adding song to the queue');
                        $('#term').focus()
                    }});
        }

    };

    App.initialize();
});