$(function() {
    var song_template = Handlebars.compile($("#song_template").html());
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
            _.bindAll(this, 'render', 'remove');
            this.model.bind('remove', this.remove);
        },
        render: function() {
            $(this.el).html(song_template(this.model.toJSON()))
            return this;
        },
        remove: function() {
            $(this.el).fadeOut(function() {
                $(this).remove();
            });
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
                        App.play(result.data.song, result.ts);
                    } else if (result.mtype == 'stop') {
                        App.stop();
                    } else if (result.mtype == 'attach') {
                        NotificationMgr.create(result.data.node_id, 'storage attached');
                    } else if (result.mtype == 'detach') {
                        NotificationMgr.create(result.data.node_id, 'storage detached');
                    } else if (result.mtype == 'login') {
                        NotificationMgr.create('', result.data, 'login')
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
        play: function (song, time_add) {
            console.debug('playing', song);
            $("#now").html(song_template(song))
            _(collection.models).each(function(item){
                if (item.get('ts_add') <= time_add) {
                    collection.remove(item);
                }
            });
            update_artist_info(song.artist);
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
            console.debug('adding', data.song);
            collection.add(data.song);
        },

        search: function(term) {
            $.ajax({url: '/play/' + encodeURI(term) + '/',
                    type: 'POST',
                    success: function(result) {
                        $('#term').val('').focus();
                    },
                    error: function() {
                        alert('Sorry, nothing found');
                        $('#term').focus()
                    }});
        }

    };

    App.initialize();
});