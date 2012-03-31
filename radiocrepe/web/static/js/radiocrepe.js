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
        el: $('body'),
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
            $('ul', this.el).append($(itemView.render().el).fadeIn());
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
                if (result) {
                    if (result.op == 'add') {
                        App.add(result['data'], result['time_add']);
                    } else if (result.op == 'play') {
                        App.play(result['data'], result['time_add']);
                    } else if (result.op == 'stop') {
                        App.stop();
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
                if (item.get('time_add') <= time_add) {
                    collection.remove(item);
                }
            });
            update_artist_info(song.artist);
        },

        stop: function() {
            $("#now").text("Nothing")
            $("#picture").hide();
        },

        add: function(song, time_add) {
            console.debug('adding', song);
            song.time_add = time_add;
            collection.add(song);
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